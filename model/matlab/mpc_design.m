function results = mpc_design()
%MPC_DESIGN  Condensed MPC for SEA torque tracking (blocked output).
%   Mirrors model/mpc.py: same linear model, same cost, same QP solved with
%   a warm-started ADMM solver (inline below — no toolboxes, mirrors the
%   firmware).  Use this to explore weights and horizons in MATLAB before
%   flashing the firmware.

p = struct('Jm', 8e-5, 'bm', 3e-5, 'Jl', 1.2e-3, 'bl', 1e-4, ...
           'ks', 1.0, 'Kt', 0.1);

% blocked-output fixture: stiff spring-damper from load to ground
% (the damper is part of the plant and must be in the prediction model)
k_block = 1e4; d_block = 50.0;
A = [0 1 0 0;
     -p.ks/p.Jm -p.bm/p.Jm  p.ks/p.Jm 0;
     0 0 0 1;
     p.ks/p.Jl 0 -(p.ks+k_block)/p.Jl -(p.bl+d_block)/p.Jl];
B = [0; p.Kt/p.Jm; 0; 0];
C = [p.ks 0 -p.ks 0];

T  = 0.5e-3;      % 2 kHz
N  = 20;          % horizon
Qy = 3e4;
Ru = 5e-3;
Sr = 0.3;
u_max  = 4.0;   % matched to the torque envelope (reference peaks ~3.8 A)
du_max = 1.5;

% exact ZOH discretization
M = expm([A*T B*T; zeros(1,5)]);
Ad = M(1:4,1:4); Bd = M(1:4,5);

% condensed matrices
F = zeros(4*N, 4); G = zeros(4*N, N);
for i = 1:N
    F((i-1)*4+1:i*4, :) = Ad^i;
    for j = 1:i
        G((i-1)*4+1:i*4, j) = Ad^(i-j) * Bd;
    end
end
Cx = kron(eye(N), C);
Qt = Qy * eye(N); Rt = Ru * eye(N);
E = zeros(N, N);
for i = 1:N
    E(i,i) = 1; if i > 1, E(i,i-1) = -1; end
end
H = 2*(G'*Cx'*Qt*Cx*G + Rt) + 2*Sr*(E'*E);
me0 = zeros(N,1); me0(1) = -2*Sr;   % u_prev contribution to the gradient

% simulate the *linear* plant in closed loop
Tsim = 2.0; n = round(Tsim/T);
x = zeros(4,1); u_prev = 0; Y = zeros(n,1); U = zeros(n,1); R = zeros(n,1);
for k = 1:n
    t = (k-1)*T;
    yref = 0.15 + 0.10*sin(2*pi*0.8*t) + 0.06*sin(2*pi*2.3*t+1) + 0.04*sin(2*pi*5.0*t);
    g = 2*(Cx*G)'*Qt*(Cx*F*x - ones(N,1)*yref) + me0*u_prev;
    lo = -u_max*ones(N,1); hi = u_max*ones(N,1);
    lo(1) = max(-u_max, u_prev - du_max); hi(1) = min(u_max, u_prev + du_max);
    Uq = admm_qp(H, g, lo, hi);     % embedded-style solver, no toolboxes
    u = Uq(1); u_prev = u;
    x = Ad*x + Bd*u;
    Y(k) = C*x; U(k) = u; R(k) = yref;
end

t = (0:n-1)' * T;
results.t = t; results.Y = Y; results.U = U; results.R = R;

figure('Name', 'MPC torque tracking (MATLAB, linear plant)');
subplot(2,1,1); plot(t, R, 'k--', t, Y, 'b'); ylabel('torque [N.m]');
legend('ref', 'response'); grid on;
subplot(2,1,2); plot(t, (Y - R)*1e3); ylabel('error [mN.m]'); xlabel('t [s]'); grid on;

fprintf('MPC design: N=%d, Qy=%.0f, Ru=%.4f, Sr=%.2f\n', N, Qy, Ru, Sr);
fprintf('RMS torque error (linear plant): %.2f mN.m\n', 1e3*sqrt(mean((Y-R).^2)));
fprintf('first inputs U(1:5): %.3f %.3f %.3f %.3f %.3f\n', U(1:5));
end

function U = admm_qp(H, g, lo, hi)
%ADMM_QP  Warm-started ADMM for the box-constrained QP (port of model/qp.py).
%   Persistent (z, lam) mirror the firmware solver, so consecutive calls in
%   the receding horizon converge in a few iterations.
    persistent z lam L n rho
    if isempty(n) || n ~= numel(g)
        n = numel(g); rho = 1.0;
        L = chol(H + rho*eye(n), 'lower');
        z = zeros(n,1); lam = zeros(n,1);
    end
    for it = 1:60
        rhs = -g + rho*(z - lam);
        u = L' \ (L \ rhs);   % solve (L*L') u = rhs — order matters!
        z_new = min(max(u + lam, lo), hi);
        lam = lam + u - z_new;
        primal = max(abs(u - z_new));
        dual = rho * max(abs(z_new - z));
        if it > 1 && primal < 1e-8 && dual < 1e-8, z = z_new; break; end
        z = z_new;
    end
    U = z;
end
