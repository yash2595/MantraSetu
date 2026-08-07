import { useEffect, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Eye, EyeOff, FileCheck, Loader2, ShieldAlert, Upload } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { SiteHeader, SiteFooter, Modal, type ModalType } from '@/components/shared';
import { authService } from '@/services/auth.service';
import { useAuth } from '@/contexts/AuthContext';

export default function SignUp() {
  const [modal, setModal] = useState<ModalType>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const location = useLocation();

  // Check URL params for role=pandit preselection
  const [userType, setUserType] = useState<'devotee' | 'pandit'>('devotee');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('role') === 'pandit' || params.get('type') === 'pandit') {
      setUserType('pandit');
    }
  }, []);

  // Devotee fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [terms, setTerms] = useState(false);

  // Pandit fields
  const [panditName, setPanditName] = useState('');
  const [panditPhone, setPanditPhone] = useState('');
  const [panditEmail, setPanditEmail] = useState('');
  const [panditPassword, setPanditPassword] = useState('');
  const [panditConfirmPassword, setPanditConfirmPassword] = useState('');
  const [showPanditPassword, setShowPanditPassword] = useState(false);
  const [showPanditConfirm, setShowPanditConfirm] = useState(false);
  const [panditCity, setPanditCity] = useState('');
  const [panditState, setPanditState] = useState('');
  const [panditLanguages, setPanditLanguages] = useState<string[]>(['Hindi', 'Sanskrit']);
  const [panditExp, setPanditExp] = useState('5-10 years');
  const [panditSpec, setPanditSpec] = useState('Vedic Pujas & Havan');
  const [aadhaarFile, setAadhaarFile] = useState<File | null>(null);
  const [certFile, setCertFile] = useState<File | null>(null);

  const [errors, setErrors] = useState<Record<string, string>>({});
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
      const errorMessage = err instanceof Error ? err.message : 'Google Registration failed.';
      setErrors({ api: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleError = () => {
    setErrors({ api: 'Google Registration was unsuccessful. Please try again.' });
  };

  const clearError = (key: string) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const validateDevotee = () => {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = 'Full name is required.';
    if (!email.trim()) {
      newErrors.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address.';
    }
    if (!password) {
      newErrors.password = 'Password is required.';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters long.';
    }
    if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match.';
    }
    if (!terms) {
      newErrors.terms = 'You must agree to the Terms of Service and Privacy Policy.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validatePandit = () => {
    const newErrors: Record<string, string> = {};
    if (!panditName.trim()) newErrors.panditName = 'Full name is required.';
    if (!panditPhone.trim()) newErrors.panditPhone = 'Mobile number is required.';
    if (!panditEmail.trim()) {
      newErrors.panditEmail = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(panditEmail)) {
      newErrors.panditEmail = 'Please enter a valid email address.';
    }
    if (!panditPassword) {
      newErrors.panditPassword = 'Password is required.';
    } else if (panditPassword.length < 8) {
      newErrors.panditPassword = 'Password must be at least 8 characters long.';
    }
    if (panditPassword !== panditConfirmPassword) {
      newErrors.panditConfirmPassword = 'Passwords do not match.';
    }
    if (!panditCity.trim()) newErrors.panditCity = 'City is required.';
    if (!panditState.trim()) newErrors.panditState = 'State is required.';
    if (panditLanguages.length === 0) newErrors.panditLanguages = 'Select at least one language.';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const isValid = userType === 'pandit' ? validatePandit() : validateDevotee();
    if (!isValid) return;

    setIsSubmitting(true);
    setErrors({});

    try {
      if (userType === 'pandit') {
        const formData = new FormData();
        formData.append('name', panditName);
        formData.append('email', panditEmail);
        formData.append('phone', panditPhone);
        formData.append('password', panditPassword);
        formData.append('confirm_password', panditConfirmPassword);
        formData.append('city', panditCity);
        formData.append('state', panditState);
        formData.append('experience', panditExp);
        formData.append('specialization', panditSpec);

        panditLanguages.forEach((lang) => {
          formData.append('languages', lang);
        });

        if (aadhaarFile) {
          formData.append('aadhaar_file', aadhaarFile);
        }
        if (certFile) {
          formData.append('certificate_file', certFile);
        }

        await authService.applyPandit(formData);
        setFormSent(true);
      } else {
        const response = await authService.signup({
          user_type: 'devotee',
          name,
          email,
          phone,
          password,
          confirm_password: confirmPassword,
        });
        
        if (response.access_token) {
          login(response.access_token, response.user);
          setFormSent(true);
          navigate("/", { replace: true });
        }
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Registration failed. Please try again.';
      setErrors({ api: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleLanguage = (lang: string) => {
    setPanditLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  };

  return (
    <div className="page-shell">
      <SiteHeader onOpenModal={setModal} />
      <main className="auth-main" data-testid="main-signup">
        <div className="auth-wrap" style={{ width: userType === 'pandit' ? 'min(100%, 580px)' : 'min(100%, 460px)', transition: 'width 200ms ease' }}>
          <div className="auth-brand">
            <Link to="/">
              <img src="/mantrasetu-logo.svg" alt="MantraSetu" />
            </Link>
          </div>

          <div className="auth-card" data-testid="card-signup">
            <span className="section-kicker">Join MantraSetu</span>
            <h1>{userType === 'pandit' ? 'Panditji Verification & Onboarding' : 'Create your account'}</h1>
            <p>{userType === 'pandit' ? 'Register your profile to receive ceremony bookings from devotees across India.' : 'Book pujas, explore tools and keep your spiritual practice close.'}</p>

            {formSent ? (
              <div className="form-success" role="status" data-testid="status-signup-success">
                <CheckCircle2 size={20} style={{ color: '#27ae60', flexShrink: 0 }} />
                <div>
                  <strong>{userType === 'pandit' ? 'Application Received!' : 'Welcome to MantraSetu!'}</strong>
                  <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: '#2d5236' }}>
                    {userType === 'pandit'
                      ? 'Thank you, Panditji. Our verification team will review your application and documents within 24 hours.'
                      : 'Your account has been created successfully. Please check your email for activation instructions.'}
                  </p>
                </div>
              </div>
            ) : (
              <form className="modal-form" onSubmit={handleSubmit} noValidate data-testid="form-signup">
                {errors.api && (
                  <div className="field-error" role="alert" style={{ padding: '0.65rem 0.85rem', background: '#fdf2f2', border: '1px solid #f8b4b4', borderRadius: '0.45rem', color: '#9b1c1c', fontSize: '0.78rem', marginBottom: '0.5rem' }}>
                    <ShieldAlert size={16} style={{ flexShrink: 0 }} /> {errors.api}
                  </div>
                )}
                {/* Account type toggle */}
                <div style={{ display: 'flex', gap: '0.5rem', padding: '0.25rem', background: '#f4ede0', borderRadius: '0.45rem', marginBottom: '0.4rem' }} role="group" aria-label="Account type">
                  {(['devotee', 'pandit'] as const).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        setUserType(type);
                        setErrors({});
                      }}
                      style={{
                        flex: 1, padding: '0.65rem', border: 0, borderRadius: '0.35rem',
                        background: userType === type ? '#fff' : 'transparent',
                        color: userType === type ? '#d96620' : '#80766c',
                        fontWeight: 800, fontSize: '0.78rem', cursor: 'pointer',
                        boxShadow: userType === type ? '0 2px 8px rgba(0,0,0,0.08)' : 'none',
                        transition: 'all 180ms ease',
                      }}
                      data-testid={`tab-usertype-${type}`}
                      aria-pressed={userType === type}
                    >
                      {type === 'devotee' ? 'I am a Devotee' : 'I am a Panditji'}
                    </button>
                  ))}
                </div>

                {/* ── PANDIT REGISTRATION FIELDS ── */}
                {userType === 'pandit' ? (
                  <>
                    <div className="field">
                      <label htmlFor="pandit-name">Full Name (Panditji)</label>
                      <input
                        id="pandit-name"
                        required
                        value={panditName}
                        onChange={(e) => setPanditName(e.target.value)}
                        placeholder="e.g. Pandit Ramesh Sharma"
                        data-testid="input-pandit-name"
                      />
                      {errors.panditName && <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditName}</span>}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                      <div className="field">
                        <label htmlFor="pandit-phone">Mobile Number</label>
                        <input
                          id="pandit-phone"
                          type="tel"
                          required
                          value={panditPhone}
                          onChange={(e) => setPanditPhone(e.target.value)}
                          placeholder="+91 XXXXX XXXXX"
                          data-testid="input-pandit-phone"
                        />
                        {errors.panditPhone && <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditPhone}</span>}
                      </div>

                      <div className="field">
                        <label htmlFor="pandit-email">Email Address</label>
                        <input
                          id="pandit-email"
                          type="email"
                          required
                          value={panditEmail}
                          onChange={(e) => setPanditEmail(e.target.value)}
                          placeholder="panditji@example.com"
                          data-testid="input-pandit-email"
                        />
                        {errors.panditEmail && <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditEmail}</span>}
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                      <div className="field">
                        <label htmlFor="pandit-password">Password</label>
                        <div style={{ position: 'relative' }}>
                          <input
                            id="pandit-password"
                            type={showPanditPassword ? 'text' : 'password'}
                            required
                            value={panditPassword}
                            onChange={(e) => {
                              setPanditPassword(e.target.value);
                              if (errors.panditPassword) clearError('panditPassword');
                            }}
                            placeholder="Min. 8 characters"
                            minLength={8}
                            style={{ paddingRight: '2.8rem' }}
                            aria-invalid={Boolean(errors.panditPassword)}
                            data-testid="input-pandit-password"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPanditPassword((s) => !s)}
                            aria-label={showPanditPassword ? 'Hide password' : 'Show password'}
                            style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', border: 0, background: 'transparent', color: '#a08870', cursor: 'pointer', padding: 0 }}
                          >
                            {showPanditPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                        {errors.panditPassword && (
                          <span className="field-error" role="alert">
                            <ShieldAlert size={14} /> {errors.panditPassword}
                          </span>
                        )}
                      </div>

                      <div className="field">
                        <label htmlFor="pandit-confirm">Confirm Password</label>
                        <div style={{ position: 'relative' }}>
                          <input
                            id="pandit-confirm"
                            type={showPanditConfirm ? 'text' : 'password'}
                            required
                            value={panditConfirmPassword}
                            onChange={(e) => {
                              setPanditConfirmPassword(e.target.value);
                              if (errors.panditConfirmPassword) clearError('panditConfirmPassword');
                            }}
                            placeholder="Re-enter password"
                            style={{ paddingRight: '2.8rem' }}
                            aria-invalid={Boolean(errors.panditConfirmPassword)}
                            data-testid="input-pandit-confirm"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPanditConfirm((s) => !s)}
                            aria-label={showPanditConfirm ? 'Hide confirm password' : 'Show confirm password'}
                            style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', border: 0, background: 'transparent', color: '#a08870', cursor: 'pointer', padding: 0 }}
                          >
                            {showPanditConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                        {errors.panditConfirmPassword && (
                          <span className="field-error" role="alert">
                            <ShieldAlert size={14} /> {errors.panditConfirmPassword}
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                      <div className="field">
                        <label htmlFor="pandit-city">City</label>
                        <input
                          id="pandit-city"
                          required
                          value={panditCity}
                          onChange={(e) => setPanditCity(e.target.value)}
                          placeholder="e.g. Varanasi, Delhi"
                          data-testid="input-pandit-city"
                        />
                        {errors.panditCity && <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditCity}</span>}
                      </div>

                      <div className="field">
                        <label htmlFor="pandit-state">State</label>
                        <input
                          id="pandit-state"
                          required
                          value={panditState}
                          onChange={(e) => setPanditState(e.target.value)}
                          placeholder="e.g. Uttar Pradesh"
                          data-testid="input-pandit-state"
                        />
                        {errors.panditState && <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditState}</span>}
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                      <div className="field">
                        <label htmlFor="pandit-exp">Years of Experience</label>
                        <select id="pandit-exp" value={panditExp} onChange={(e) => setPanditExp(e.target.value)} data-testid="select-pandit-exp">
                          <option value="1-5 years">1 - 5 Years</option>
                          <option value="5-10 years">5 - 10 Years</option>
                          <option value="10-20 years">10 - 20 Years</option>
                          <option value="20+ years">20+ Years</option>
                        </select>
                      </div>

                      <div className="field">
                        <label htmlFor="pandit-spec">Primary Specialization</label>
                        <select id="pandit-spec" value={panditSpec} onChange={(e) => setPanditSpec(e.target.value)} data-testid="select-pandit-spec">
                          <option value="Vedic Pujas & Havan">Vedic Pujas & Havan</option>
                          <option value="Jyotish & Kundali">Jyotish & Kundali Analysis</option>
                          <option value="Sanskar Ceremonies">Shodasha Sanskar Ceremonies</option>
                          <option value="Katha & Pravachan">Katha & Spiritual Pravachan</option>
                        </select>
                      </div>
                    </div>

                    <div className="field">
                      <label>Languages Spoken</label>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.2rem' }}>
                        {['Hindi', 'Sanskrit', 'English', 'Gujarati', 'Marathi', 'Bengali', 'Tamil', 'Telugu'].map((lang) => {
                          const active = panditLanguages.includes(lang);
                          return (
                            <button
                              key={lang}
                              type="button"
                              onClick={() => toggleLanguage(lang)}
                              style={{
                                padding: '0.3rem 0.65rem',
                                borderRadius: '0.35rem',
                                border: '1px solid',
                                borderColor: active ? '#ee7c2b' : '#e5d5c1',
                                background: active ? '#fff0e2' : '#fffdf9',
                                color: active ? '#d96620' : '#68645f',
                                fontSize: '0.72rem',
                                fontWeight: active ? 800 : 500,
                                cursor: 'pointer',
                              }}
                            >
                              {lang} {active ? '✓' : ''}
                            </button>
                          );
                        })}
                      </div>
                      {errors.panditLanguages && <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditLanguages}</span>}
                    </div>

                    {/* Document Upload Placeholders */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem', marginTop: '0.4rem' }}>
                      <div className="field">
                        <label>Aadhaar Identity Proof</label>
                        <label
                          style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
                            padding: '0.9rem', border: '1px dashed #d99c6b', borderRadius: '0.45rem', background: '#fffaf2', cursor: 'pointer', textAlign: 'center'
                          }}
                        >
                          <Upload size={18} color="#d96620" />
                          <span style={{ fontSize: '0.7rem', color: '#7a4b2c', fontWeight: 700 }}>
                            {aadhaarFile ? <><FileCheck size={14} color="#27ae60" /> {aadhaarFile.name}</> : 'Upload Aadhaar PDF/Image'}
                          </span>
                          <input type="file" style={{ display: 'none' }} onChange={(e) => setAadhaarFile(e.target.files?.[0] || null)} />
                        </label>
                      </div>

                      <div className="field">
                        <label>Vedic Certificate</label>
                        <label
                          style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
                            padding: '0.9rem', border: '1px dashed #d99c6b', borderRadius: '0.45rem', background: '#fffaf2', cursor: 'pointer', textAlign: 'center'
                          }}
                        >
                          <Upload size={18} color="#d96620" />
                          <span style={{ fontSize: '0.7rem', color: '#7a4b2c', fontWeight: 700 }}>
                            {certFile ? <><FileCheck size={14} color="#27ae60" /> {certFile.name}</> : 'Upload Certificate'}
                          </span>
                          <input type="file" style={{ display: 'none' }} onChange={(e) => setCertFile(e.target.files?.[0] || null)} />
                        </label>
                      </div>
                    </div>

                    <button
                      className="button button-primary"
                      style={{ justifySelf: 'stretch', width: '100%', marginTop: '0.6rem' }}
                      type="submit"
                      disabled={isSubmitting}
                      aria-busy={isSubmitting}
                      data-testid="button-submit-pandit-signup"
                    >
                      {isSubmitting ? (
                        <><Loader2 size={16} className="animate-spin" /> Submitting Application...</>
                      ) : (
                        <>Submit Panditji Application <ArrowRight size={15} /></>
                      )}
                    </button>
                  </>
                ) : (
                  /* ── DEVOTEE REGISTRATION FIELDS ── */
                  <>
                    <div className="field">
                      <label htmlFor="signup-name">Full name</label>
                      <input
                        id="signup-name"
                        name="name"
                        required
                        value={name}
                        onChange={(e) => {
                          setName(e.target.value);
                          if (errors.name) clearError('name');
                        }}
                        placeholder="Your full name"
                        aria-invalid={Boolean(errors.name)}
                        aria-describedby={errors.name ? 'name-error' : undefined}
                        data-testid="input-signup-name"
                      />
                      {errors.name && (
                        <span className="field-error" id="name-error" role="alert">
                          <ShieldAlert size={14} /> {errors.name}
                        </span>
                      )}
                    </div>

                    <div className="field">
                      <label htmlFor="signup-email">Email address</label>
                      <input
                        id="signup-email"
                        name="email"
                        type="email"
                        required
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (errors.email) clearError('email');
                        }}
                        placeholder="you@example.com"
                        aria-invalid={Boolean(errors.email)}
                        aria-describedby={errors.email ? 'email-error' : undefined}
                        data-testid="input-signup-email"
                      />
                      {errors.email && (
                        <span className="field-error" id="email-error" role="alert">
                          <ShieldAlert size={14} /> {errors.email}
                        </span>
                      )}
                    </div>

                    <div className="field">
                      <label htmlFor="signup-phone">Mobile number <span style={{ color: '#a08870', fontWeight: 400 }}>(optional)</span></label>
                      <input
                        id="signup-phone"
                        name="phone"
                        type="tel"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="+91 XXXXX XXXXX"
                        data-testid="input-signup-phone"
                      />
                    </div>

                    <div className="field">
                      <label htmlFor="signup-password">Password</label>
                      <div style={{ position: 'relative' }}>
                        <input
                          id="signup-password"
                          name="password"
                          type={showPassword ? 'text' : 'password'}
                          required
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            if (errors.password) clearError('password');
                          }}
                          placeholder="Create a password (min. 8 characters)"
                          minLength={8}
                          style={{ paddingRight: '2.8rem' }}
                          aria-invalid={Boolean(errors.password)}
                          aria-describedby={errors.password ? 'password-error' : undefined}
                          data-testid="input-signup-password"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword((s) => !s)}
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                          style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', border: 0, background: 'transparent', color: '#a08870', cursor: 'pointer', padding: 0 }}
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

                    <div className="field">
                      <label htmlFor="signup-confirm">Confirm password</label>
                      <div style={{ position: 'relative' }}>
                        <input
                          id="signup-confirm"
                          name="confirm"
                          type={showConfirm ? 'text' : 'password'}
                          required
                          value={confirmPassword}
                          onChange={(e) => {
                            setConfirmPassword(e.target.value);
                            if (errors.confirmPassword) clearError('confirmPassword');
                          }}
                          placeholder="Re-enter your password"
                          style={{ paddingRight: '2.8rem' }}
                          aria-invalid={Boolean(errors.confirmPassword)}
                          aria-describedby={errors.confirmPassword ? 'confirm-error' : undefined}
                          data-testid="input-signup-confirm"
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirm((s) => !s)}
                          aria-label={showConfirm ? 'Hide confirm password' : 'Show confirm password'}
                          style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', border: 0, background: 'transparent', color: '#a08870', cursor: 'pointer', padding: 0 }}
                        >
                          {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                      {errors.confirmPassword && (
                        <span className="field-error" id="confirm-error" role="alert">
                          <ShieldAlert size={14} /> {errors.confirmPassword}
                        </span>
                      )}
                    </div>

                    <div className="field">
                      <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.75rem', color: '#68645f', cursor: 'pointer', lineHeight: 1.5 }}>
                        <input
                          type="checkbox"
                          required
                          checked={terms}
                          onChange={(e) => {
                            setTerms(e.target.checked);
                            if (errors.terms) clearError('terms');
                          }}
                          style={{ marginTop: '0.15rem', flexShrink: 0 }}
                          data-testid="checkbox-terms"
                        />
                        <span>
                          I agree to MantraSetu's{' '}
                          <a href="#" onClick={(e) => e.preventDefault()} style={{ color: '#d96620', textDecoration: 'none', fontWeight: 700 }}>
                            Terms of Service
                          </a>{' '}
                          and{' '}
                          <a href="#" onClick={(e) => e.preventDefault()} style={{ color: '#d96620', textDecoration: 'none', fontWeight: 700 }}>
                            Privacy Policy
                          </a>
                        </span>
                      </label>
                      {errors.terms && (
                        <span className="field-error" id="terms-error" role="alert">
                          <ShieldAlert size={14} /> {errors.terms}
                        </span>
                      )}
                    </div>

                    <button
                      className="button button-primary"
                      style={{ justifySelf: 'stretch', width: '100%' }}
                      type="submit"
                      disabled={isSubmitting}
                      aria-busy={isSubmitting}
                      data-testid="button-submit-signup"
                    >
                      {isSubmitting ? (
                        <><Loader2 size={16} className="animate-spin" /> Creating account...</>
                      ) : (
                        <>Create account <ArrowRight size={15} /></>
                      )}
                    </button>
                  </>
                )}
              </form>
            )}

            {userType === 'devotee' && !formSent && (
              <>
                <div className="auth-divider">or continue with</div>
                <div className="auth-google-btn-wrapper" style={{ display: 'flex', justifySelf: 'stretch', width: '100%' }}>
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={handleGoogleError}
                    shape="rectangular"
                    text="signup_with"
                    size="large"
                    width="100%"
                  />
                </div>
              </>
            )}

            <p className="auth-link" data-testid="link-to-login">
              Already have an account? <Link to="/login">Sign in</Link>
            </p>
          </div>
        </div>
      </main>
      <SiteFooter />
      <Modal modal={modal} onClose={() => setModal(null)} />
    </div>
  );
}
