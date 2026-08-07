import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Eye, EyeOff, Loader2, ShieldAlert } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { SiteHeader, SiteFooter, Modal, type ModalType } from '@/components/shared';
import { authService } from '@/services/auth.service';
import { useAuth } from '@/contexts/AuthContext';

export default function Login() {
  const [modal, setModal] = useState<ModalType>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; api?: string }>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formSent, setFormSent] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleGoogleSuccess = async (credentialResponse: any) => {
    if (!credentialResponse.credential) {
      setErrors({ api: 'Google login failed: No credential received.' });
      return;
    }
    try {
      setIsSubmitting(true);
      const res = await authService.googleLogin(credentialResponse.credential);
      if (res.access_token) {
        login(res.access_token, res.user);
        setFormSent(true);
        navigate("/", { replace: true });
      } else {
        setErrors({ api: 'Google login failed: No access token received.' });
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Google Login failed.';
      setErrors({ api: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleError = () => {
    setErrors({ api: 'Google Login was unsuccessful. Please try again.' });
  };

  const validate = () => {
    const newErrors: { email?: string; password?: string; api?: string } = {};
    if (!email.trim()) {
      newErrors.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address.';
    }

    if (!password) {
      newErrors.password = 'Password is required.';
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setErrors({});

    try {
      const response = await authService.login({ email, password, remember });
      if (response.access_token) {
        login(response.access_token, response.user);
        setFormSent(true);
        navigate("/", { replace: true });
      } else {
        setErrors({ api: 'Login failed: No access token received.' });
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Invalid credentials. Please try again.';
      setErrors({ api: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <SiteHeader onOpenModal={setModal} />
      <main className="auth-main" data-testid="main-login">
        <div className="auth-wrap">
          <div className="auth-brand">
            <Link to="/">
              <img src="/mantrasetu-logo.svg" alt="MantraSetu" />
            </Link>
          </div>

          <div className="auth-card" data-testid="card-login">
            <span className="section-kicker">Welcome back</span>
            <h1>Sign in to MantraSetu</h1>
            <p>Access your pujas, kundali charts and spiritual tools.</p>

            {formSent ? (
              <div className="form-success" role="status" data-testid="status-login-success">
                <CheckCircle2 size={18} style={{ color: '#27ae60', flexShrink: 0 }} />
                <span>You have been signed in successfully. Welcome back to MantraSetu!</span>
              </div>
            ) : (
              <form className="modal-form" onSubmit={handleSubmit} noValidate data-testid="form-login">
                {errors.api && (
                  <div className="field-error" role="alert" style={{ padding: '0.65rem 0.85rem', background: '#fdf2f2', border: '1px solid #f8b4b4', borderRadius: '0.45rem', color: '#9b1c1c', fontSize: '0.78rem', marginBottom: '0.5rem' }}>
                    <ShieldAlert size={16} style={{ flexShrink: 0 }} /> {errors.api}
                  </div>
                )}
                <div className="field">
                  <label htmlFor="login-email">Email address</label>
                  <input
                    id="login-email"
                    name="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }));
                    }}
                    placeholder="you@example.com"
                    aria-invalid={Boolean(errors.email)}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                    data-testid="input-login-email"
                  />
                  {errors.email && (
                    <span className="field-error" id="email-error" role="alert">
                      <ShieldAlert size={14} /> {errors.email}
                    </span>
                  )}
                </div>

                <div className="field">
                  <label htmlFor="login-password">
                    Password
                    <a
                      href="#"
                      onClick={(e) => e.preventDefault()}
                      style={{ float: 'right', color: '#d96620', fontSize: '0.72rem', fontWeight: 700, textDecoration: 'none' }}
                      data-testid="link-forgot-password"
                    >
                      Forgot password?
                    </a>
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      id="login-password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }));
                      }}
                      placeholder="Enter your password"
                      style={{ paddingRight: '2.8rem' }}
                      aria-invalid={Boolean(errors.password)}
                      aria-describedby={errors.password ? 'password-error' : undefined}
                      data-testid="input-login-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((s) => !s)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', border: 0, background: 'transparent', color: '#a08870', cursor: 'pointer', padding: 0 }}
                      data-testid="button-toggle-password"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.password && (
                    <span className="field-error" id="password-error" role="alert">
                      <ShieldAlert size={14} /> {errors.password}
                    </span>
                  )}
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', color: '#68645f', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    name="remember"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    data-testid="checkbox-remember"
                  />
                  Remember me for 30 days
                </label>

                <button
                  className="button button-primary"
                  style={{ justifySelf: 'stretch', width: '100%' }}
                  type="submit"
                  disabled={isSubmitting}
                  aria-busy={isSubmitting}
                  data-testid="button-submit-login"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Signing in...
                    </>
                  ) : (
                    <>
                      Continue <ArrowRight size={15} />
                    </>
                  )}
                </button>
              </form>
            )}

            <div className="auth-divider">or continue with</div>
            <div className="auth-google-btn-wrapper" style={{ display: 'flex', justifySelf: 'stretch', width: '100%' }}>
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                shape="rectangular"
                text="continue_with"
                size="large"
                width="100%"
              />
            </div>

            <p style={{ marginTop: '1.2rem', textAlign: 'center', fontSize: '0.82rem', color: '#68645f' }}>
              Don't have an account? <Link to="/sign-up">Create one for free</Link>
            </p>
          </div>
        </div>
      </main>
      <SiteFooter />
      <Modal modal={modal} onClose={() => setModal(null)} />
    </div>
  );
}
