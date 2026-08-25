function idp = system_id()
%SYSTEM_ID  Integrated-equation least squares for SEA inertia/friction.
%   Mirrors learn/system_id.py.  Inputs (here: from a chirp simulation of
%   the plant); on the bench, feed logged (i_q, theta_m, theta_l, omega_m,
%   omega_l) at 2 kHz from the firmware telemetry.

p = struct('Kt', 0.1, 'Jm', 8e-5, 'Jl', 1.2e-3, 'ks', 0.985, 'knl', 0);
[Tsim, fs] = deal(6.0, 2000);
[t, x] = sea_plant_model(p, @(t) excitation(t), Tsim);
% resample to fs
tt = (0:1/fs:Tsim)';
xm = interp1(t, x, tt);
theta_m = xm(:,1); omega_m = xm(:,2);
theta_l = xm(:,3); omega_l = xm(:,4); iq = xm(:,5);
u = excitation(tt);

delta = theta_m - theta_l;
tau_s = p.ks * delta + p.knl * delta.^3;   % calibrated spring torque
dt = 1/fs; eps_ = 0.05;

% load side: Jl*dwl = sum(tau_s) - bl*sum(wl) - tau_c_l*sum(tanh(wl/eps))
Xl = [omega_l - omega_l(1), cumsum(omega_l)*dt, cumsum(tanh(omega_l/eps_))*dt];
Yl = cumsum(tau_s)*dt;
beta_l = Xl \ Yl;
Jl = beta_l(1); bl = beta_l(2); tau_c_l = beta_l(3);

% motor side: Jm*dwm = Kt*sum(iq) - bm*sum(wm) - sum(tau_s) - tau_c_m*sum(tanh)
Xm_ = [omega_m - omega_m(1), cumsum(omega_m)*dt, cumsum(tanh(omega_m/eps_))*dt];
Ym = p.Kt*cumsum(iq)*dt - cumsum(tau_s)*dt;
beta_m = Xm_ \ Ym;
Jm = beta_m(1); bm = beta_m(2); tau_c_m = beta_m(3);

idp = struct('Jm', Jm, 'bm', bm, 'Jl', Jl, 'bl', bl, ...
             'tau_c_m', tau_c_m, 'tau_c_l', tau_c_l, 'ks', p.ks);
fprintf('Identified: Jm=%.3e (true %.3e), Jl=%.3e (true %.3e), ks=%.3f\n', ...
        Jm, p.Jm, Jl, p.Jl, p.ks);
end

function u = excitation(t)
%EXCITATION  Chirp + PRBS + slow square current, clipped to +/-1.5 A.
%   Mirrors learn/system_id.py::collect_excitation (wide velocity range so
%   the integrated-equation regressors stay well conditioned).
    T = 6.0; f0 = 0.3; f1 = 10.0;
    chirp = sin(2*pi*(f0*t + 0.5*(f1-f0)/T*t.^2));
    prbs = 0.25*randn(size(t));
    square = 0.3*sign(sin(2*pi*0.4*t));
    u = max(-1.5, min(1.5, 0.9*chirp + prbs + square));
end
