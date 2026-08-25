function [t, x] = sea_plant_model(varargin)
%SEA_PLANT_MODEL  Two-mass SEA plant with friction and cogging.
%   [t, x] = sea_plant_model()          % defaults
%   [t, x] = sea_plant_model(p, u_fn, T) % custom params/current profile
%
%   Mirrors model/plant.py (the digital twin): same states, same friction /
%   cogging / ripple / current-loop structure, integrated with fixed-step RK4
%   at dt = 10 us (100 kHz) so the ~0.2 ms electrical time constant is
%   resolved.  Use this to validate the Simulink model against the digital
%   twin before hardware bring-up.
%
%   x = [theta_m, omega_m, theta_l, omega_l, iq]

p = struct( ...
    'R', 1.5, 'L', 3e-4, 'Kt', 0.1, 'Ke', 0.1, ...
    'Jm', 8e-5, 'bm', 3e-5, ...
    'tau_c_m', 8e-3, 'tau_st_m', 12e-3, 'w_st_m', 0.6, 'bv_m', 2e-4, ...
    'cog_A6', 3e-3, 'cog_phi6', 0.3, 'cog_A12', 1.5e-3, 'cog_phi12', 1.1, ...
    'rip_frac', 0.01, ...
    'ks', 1.0, 'knl', 0.0, ...
    'Jl', 1.2e-3, 'bl', 1e-4, ...
    'tau_c_l', 4e-3, 'tau_st_l', 6e-3, 'w_st_l', 0.4, 'bv_l', 8e-5, ...
    'Vbus', 24.0, 'f_cur', 10e3, 'w_cur_bw', 2*pi*1500, 'dt', 1e-5);
if nargin >= 1   % merge override fields into defaults
    flds = fieldnames(varargin{1});
    for i = 1:numel(flds), p.(flds{i}) = varargin{1}.(flds{i}); end
end
if nargin >= 2, u_fn = varargin{2}; else, u_fn = @(t) 1.0*(t < 0.1); end
if nargin >= 3, T = varargin{3}; else, T = 1.0; end

dt = p.dt;
steps_per_cur = max(1, round(1.0/(p.f_cur*dt)));
n = round(T/dt);
x = zeros(n+1, 5); t = (0:n)'*dt;
s = zeros(5, 1);                 % theta_m, omega_m, theta_l, omega_l, iq
int_state = 0; vq = 0; cur_tick = 0;
x(1,:) = s.';
for k = 1:n
    tk = (k-1)*dt;
    iq_ref = u_fn(tk);
    if cur_tick == 0
        % PI current loop + back-EMF feedforward, conditional anti-windup
        err = iq_ref - s(5);
        int_state = int_state + p.R*p.w_cur_bw * err * dt;
        vq_raw = int_state + p.L*p.w_cur_bw * err + p.Ke*s(2);
        vq = max(-p.Vbus/sqrt(3), min(p.Vbus/sqrt(3), vq_raw));
        if vq ~= vq_raw   % saturated: freeze the integral
            int_state = int_state - p.R*p.w_cur_bw * err * dt;
        end
    end
    s = rk4_step(s, vq, p, dt);
    cur_tick = mod(cur_tick + 1, steps_per_cur);
    x(k+1,:) = s;
end
end

function s1 = rk4_step(s, vq, p, dt)
    k1 = sea_rhs(s, vq, p);
    k2 = sea_rhs(s + 0.5*dt*k1, vq, p);
    k3 = sea_rhs(s + 0.5*dt*k2, vq, p);
    k4 = sea_rhs(s + dt*k3, vq, p);
    s1 = s + (dt/6)*(k1 + 2*k2 + 2*k3 + k4);
end

function xd = sea_rhs(s, vq, p)
    tm = s(1); wm = s(2); tl = s(3); wl = s(4); iq = s(5);
    d = tm - tl;
    tau_s = p.ks * d + p.knl * d.^3;
    tau_motor = p.Kt * iq + p.cog_A6*sin(6*tm + p.cog_phi6) ...
                + p.cog_A12*sin(12*tm + p.cog_phi12) ...
                + iq * p.rip_frac * sin(6*tm);
    sm = tanh(wm/0.05); sl = tanh(wl/0.05);
    f_m = (p.tau_c_m + (p.tau_st_m - p.tau_c_m)*exp(-(wm/p.w_st_m).^2)) * sm + p.bv_m*wm;
    f_l = (p.tau_c_l + (p.tau_st_l - p.tau_c_l)*exp(-(wl/p.w_st_l).^2)) * sl + p.bv_l*wl;
    xd = [wm;
          (tau_motor - tau_s - f_m - p.bm*wm) / p.Jm;
          wl;
          (tau_s - f_l - p.bl*wl) / p.Jl;
          (vq - p.R*iq - p.Ke*wm) / p.L];
end
