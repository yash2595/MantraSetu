import { useEffect, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Award,
  CheckCircle2,
  Eye,
  EyeOff,
  FileCheck,
  Film,
  FileText,
  Image as ImageIcon,
  Loader2,
  Plus,
  RotateCcw,
  ShieldAlert,
  Trash2,
  Upload,
  User,
  X,
} from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { SiteHeader, SiteFooter, Modal, type ModalType } from '@/components/shared';
import { authService } from '@/services/auth.service';
import { useAuth } from '@/contexts/AuthContext';
import { useSaarthi } from '@/components/saarthi/SaarthiContext';
import { getPersistableData } from '@/utils/formSecurity';

const specializationsCatalog = [
  'वैदिक अनुष्ठान (Vedic Rituals)',
  'ज्योतिष (Astrology)',
  'विवाह संस्कार (Marriage Ceremonies)',
  'गृह प्रवेश (House Warming)',
  'नामकरण (Naming Ceremony)',
  'अन्नप्राशन (First Feeding)',
  'मुंडन (Hair Cutting)',
  'यज्ञ (Yajna)',
  'पूजा (Puja)',
  'हवन (Havan)',
  'संस्कार (Sanskar)',
  'व्रत (Vrat)',
  'Rudrabhishek & Mahamrityunjaya',
  'Navgraha Shanti & Dosha Nivaran',
  'Satyanarayan Katha & Path',
  'Shodasha Sanskar Ceremonies',
  'अन्य (Other)',
];

const languagesList = [
  'Hindi',
  'Sanskrit',
  'English',
  'Tamil',
  'Telugu',
  'Bengali',
  'Gujarati',
  'Marathi',
  'Kannada',
  'Malayalam',
  'Punjabi',
  'Assamese',
  'Odia',
];

const serviceAreasCatalog = [
  'Delhi NCR',
  'Mumbai',
  'Bangalore',
  'Chennai',
  'Kolkata',
  'Hyderabad',
  'Pune',
  'Ahmedabad',
  'Jaipur',
  'Lucknow',
  'Online Puja',
  'PAN India',
  'North Zone',
  'South Zone',
  'East Zone',
  'West Zone',
  'Other',
];

export default function SignUp() {
  const { announceMessage } = useSaarthi();
  const [modal, setModal] = useState<ModalType>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const location = useLocation();

  // Check URL params for role=pandit preselection
  const [userType, setUserType] = useState<'devotee' | 'pandit'>('devotee');

  useEffect(() => {
    const searchStr = location.search || window.location.search;
    const params = new URLSearchParams(searchStr);
    const roleParam = params.get('role') || params.get('type');
    if (roleParam === 'pandit') {
      setUserType('pandit');
    } else if (roleParam === 'devotee') {
      setUserType('devotee');
    }
  }, [location.search, location.pathname, location.key]);

  // Devotee fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [terms, setTerms] = useState(false);

  // Pandit multi-step onboarding state
  const [panditStep, setPanditStep] = useState<1 | 2 | 3>(1);
  const [activeField, setActiveField] = useState<string>('pandit-avatar');

  // Step 1: Personal & Contact Details
  const [panditFirstName, setPanditFirstName] = useState('');
  const [panditLastName, setPanditLastName] = useState('');
  const [panditName, setPanditName] = useState('');
  const [panditGender, setPanditGender] = useState<'Male' | 'Female' | 'Other'>('Male');
  const [panditPhone, setPanditPhone] = useState('');
  const [panditEmail, setPanditEmail] = useState('');
  const [panditCity, setPanditCity] = useState('');
  const [panditState, setPanditState] = useState('');
  const [panditAvailabilityMode, setPanditAvailabilityMode] = useState('Both');
  const [selectedServiceAreas, setSelectedServiceAreas] = useState<string[]>(['Delhi NCR', 'Online Puja']);
  const [panditServiceAreas, setPanditServiceAreas] = useState('');
  const [profilePhotoPreview, setProfilePhotoPreview] = useState<string | null>(null);

  // Step 2: Vedic Qualifications, Experience & Achievements
  const [panditExp, setPanditExp] = useState('5');
  const [panditEducation, setPanditEducation] = useState('');
  const [panditGurukul, setPanditGurukul] = useState('');
  const [panditSpec, setPanditSpec] = useState('वैदिक अनुष्ठान (Vedic Rituals)');
  const [selectedSpecs, setSelectedSpecs] = useState<string[]>(['वैदिक अनुष्ठान (Vedic Rituals)']);
  const [panditLanguages, setPanditLanguages] = useState<string[]>(['Hindi', 'Sanskrit']);
  const [panditAchievements, setPanditAchievements] = useState<string[]>(['']);
  const [panditBio, setPanditBio] = useState('');

  // Step 3: Identity Verification, Gallery & Security
  const [aadhaarFile, setAadhaarFile] = useState<File | null>(null);
  const [certFile, setCertFile] = useState<File | null>(null);
  const [galleryFiles, setGalleryFiles] = useState<File[]>([]);
  const [galleryError, setGalleryError] = useState<string | null>(null);
  const [panditPassword, setPanditPassword] = useState('');
  const [panditConfirmPassword, setPanditConfirmPassword] = useState('');
  const [showPanditPassword, setShowPanditPassword] = useState(false);
  const [showPanditConfirm, setShowPanditConfirm] = useState(false);
  const [panditCodeOfConduct, setPanditCodeOfConduct] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formSent, setFormSent] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  // Sync first and last name into panditName
  const handleFirstNameChange = (val: string) => {
    setPanditFirstName(val);
    const combined = `${val} ${panditLastName}`.trim();
    setPanditName(combined);
    if (errors.panditFirstName) clearError('panditFirstName');
    if (errors.panditName) clearError('panditName');
  };

  const handleLastNameChange = (val: string) => {
    setPanditLastName(val);
    const combined = `${panditFirstName} ${val}`.trim();
    setPanditName(combined);
    if (errors.panditLastName) clearError('panditLastName');
    if (errors.panditName) clearError('panditName');
  };

  // ── SESSION STORAGE PERSISTENCE & RELOAD RESTORATION ──
  // Smart detection: only restore draft if an active voice session exists (mid-fill F5 refresh).
  // On a completely fresh visit (new tab / new browser session), saarthi_session_id is absent
  // from sessionStorage → clear any stale draft and start blank.
  useEffect(() => {
    const loadDraft = () => {
      const saved = sessionStorage.getItem('ms_saarthi_pandit_form_data');
      if (!saved) return; // Nothing to restore

      // KEY DISTINCTION: Is there an active voice onboarding session?
      // saarthi_session_id is written by useSaarthiVoice.ts on WebSocket CONNECT.
      // Exists  → mid-fill F5 refresh → RESTORE form data normally.
      // Absent  → new browser visit  → CLEAR stale draft so form is blank.
      const hasActiveVoiceSession = !!sessionStorage.getItem('saarthi_session_id');

      if (!hasActiveVoiceSession) {
        sessionStorage.removeItem('ms_saarthi_pandit_form_data');
        setPanditStep(1);
        console.log('[PANDIT-STEP-TRACE] New visit (no active voice session). Reset panditStep to 1 and cleared draft.');
        return;
      }

      // Active session exists → safe to restore (mid-fill F5 refresh)
      try {
        const data = JSON.parse(saved);

        // ── Step position (CRITICAL: restore saved step during mid-form refresh) ──
        if (data.panditStep && [1, 2, 3].includes(data.panditStep)) {
          console.log(`[PANDIT-STEP-TRACE] Restoring saved panditStep from draft: ${data.panditStep}`);
          setPanditStep(data.panditStep as 1 | 2 | 3);
        }

        // ── Step 1: Personal & Contact ──
        if (data.panditFirstName) setPanditFirstName(data.panditFirstName);
        if (data.panditLastName) setPanditLastName(data.panditLastName);
        if (data.panditFirstName || data.panditLastName) {
          setPanditName(`${data.panditFirstName ?? ''} ${data.panditLastName ?? ''}`.trim());
        }
        if (data.panditGender) setPanditGender(data.panditGender);
        if (data.panditPhone) setPanditPhone(data.panditPhone);
        if (data.panditEmail) setPanditEmail(data.panditEmail);
        if (data.panditCity) setPanditCity(data.panditCity);
        if (data.panditState) setPanditState(data.panditState);
        if (data.panditAvailabilityMode) setPanditAvailabilityMode(data.panditAvailabilityMode);
        if (Array.isArray(data.selectedServiceAreas)) setSelectedServiceAreas(data.selectedServiceAreas);

        // ── Step 2: Vedic Qualifications, Experience & Achievements ──
        if (data.panditExp) setPanditExp(data.panditExp);
        if (data.panditEducation) setPanditEducation(data.panditEducation);
        if (data.panditGurukul) setPanditGurukul(data.panditGurukul);
        if (data.panditSpec) setPanditSpec(data.panditSpec);
        if (Array.isArray(data.selectedSpecs)) setSelectedSpecs(data.selectedSpecs);
        if (Array.isArray(data.panditLanguages)) setPanditLanguages(data.panditLanguages);
        if (Array.isArray(data.panditAchievements)) setPanditAchievements(data.panditAchievements);
        if (data.panditBio) setPanditBio(data.panditBio);

        console.log('[PERSISTENCE] Mid-fill refresh: restored Pandit form draft from sessionStorage.');
      } catch (e) {
        console.error('[PERSISTENCE] Failed to parse sessionStorage data', e);
      }
    };
    loadDraft();
  }, []);

  // ── VOICE ASSISTANT STEP SYNC ──
  // Listen for active_field changes from Saarthi voice agent and switch UI tab/step dynamically
  useEffect(() => {
    const handleStepSync = (e: Event) => {
      const customEvt = e as CustomEvent<{ step: 1 | 2 | 3; activeField: string }>;
      if (customEvt.detail && customEvt.detail.step) {
        console.log(`[PANDIT-STEP-TRACE] Received saarthi-set-step event. Changing panditStep -> ${customEvt.detail.step} (Triggered by activeField: "${customEvt.detail.activeField}")`);
        setPanditStep(customEvt.detail.step);
      }
      if (customEvt.detail && customEvt.detail.activeField) {
        setActiveField(customEvt.detail.activeField);
      } else if (customEvt.detail && customEvt.detail.step) {
        const defaults: Record<number, string> = { 1: 'pandit-first-name', 2: 'pandit-exp', 3: 'pandit-certFile' };
        setActiveField(defaults[customEvt.detail.step] || 'pandit-first-name');
      }
    };
    window.addEventListener('saarthi-set-step', handleStepSync);
    return () => window.removeEventListener('saarthi-set-step', handleStepSync);
  }, []);

  // ── ACTIVE FIELD & STEP SYNCHRONIZATION EFFECT ──
  useEffect(() => {
    console.log('[SYNC-DEBUG] activeField:', activeField, '| step:', panditStep);

    const stepDefaults: Record<number, string> = {
      1: 'pandit-avatar',
      2: 'pandit-exp',
      3: 'pandit-certFile'
    };
    const step2Fields = ['pandit-exp', 'pandit-gurukul', 'pandit-education', 'pandit-languages', 'pandit-spec', 'pandit-achievements', 'pandit-bio'];
    const step3Fields = ['pandit-certFile', 'pandit-aadhaarFile', 'pandit-galleryFiles', 'pandit-password', 'pandit-confirm'];

    const currentFieldStep = step2Fields.includes(activeField) ? 2 : step3Fields.includes(activeField) ? 3 : 1;

    if (currentFieldStep !== panditStep) {
      const newField = stepDefaults[panditStep] || 'pandit-avatar';
      console.log(`[SYNC-DEBUG] Step changed to ${panditStep}. Updating activeField: "${activeField}" -> "${newField}"`);
      setActiveField(newField);
    }
  }, [panditStep, activeField]);




  // ── SESSION STORAGE SAVE (fires on every relevant state change) ──
  useEffect(() => {
    if (userType === 'pandit') {
      const timer = setTimeout(() => {
        try {
          const payload = {
            panditStep,
            panditFirstName,
            panditLastName,
            panditName,
            panditGender,
            panditPhone,
            panditEmail,
            panditCity,
            panditState,
            panditAvailabilityMode,
            selectedServiceAreas,
            panditExp,
            panditEducation,
            panditGurukul,
            panditSpec,
            selectedSpecs,
            panditLanguages,
            panditAchievements,
            panditBio,
            panditPassword,
            panditConfirmPassword,
          };
          const safePayload = getPersistableData(payload);
          sessionStorage.setItem('ms_saarthi_pandit_form_data', JSON.stringify(safePayload));
        } catch (e) {
          console.error('[PERSISTENCE] Failed to save session storage', e);
        }
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [
    userType,
    panditStep,
    panditFirstName, panditLastName, panditName, panditGender,
    panditPhone, panditEmail, panditCity, panditState,
    panditAvailabilityMode, selectedServiceAreas,
    panditExp, panditEducation, panditGurukul,
    panditSpec, selectedSpecs, panditLanguages,
    panditAchievements, panditBio,
    panditPassword, panditConfirmPassword,
  ]);

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
        navigate('/', { replace: true });
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

  const toggleLanguage = (lang: string) => {
    setPanditLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
    if (errors.panditLanguages) clearError('panditLanguages');
  };

  const toggleSpecialization = (spec: string) => {
    setSelectedSpecs((prev) => {
      const next = prev.includes(spec) ? prev.filter((s) => s !== spec) : [...prev, spec];
      if (next.length > 0) {
        setPanditSpec(next[0]);
      }
      return next;
    });
    if (errors.panditSpec) clearError('panditSpec');
  };

  const toggleServiceArea = (area: string) => {
    setSelectedServiceAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    );
  };

  const addAchievement = () => {
    setPanditAchievements((prev) => [...prev, '']);
  };

  const updateAchievement = (index: number, val: string) => {
    setPanditAchievements((prev) => {
      const next = [...prev];
      next[index] = val;
      return next;
    });
  };

  const removeAchievement = (index: number) => {
    setPanditAchievements((prev) => {
      const next = prev.filter((_, i) => i !== index);
      return next.length === 0 ? [''] : next;
    });
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfilePhotoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleGallerySelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setGalleryError(null);
    const newFiles = Array.from(files);

    if (galleryFiles.length + newFiles.length > 7) {
      setGalleryError('Maximum 7 files allowed in Gallery.');
      return;
    }

    for (const f of newFiles) {
      const isVideo = f.type.startsWith('video/');
      const isImg = f.type.startsWith('image/');
      const isPdf = f.type === 'application/pdf' || f.name.endsWith('.pdf');

      if (!isVideo && !isImg && !isPdf) {
        setGalleryError(`Unsupported file format: ${f.name}. Allowed: Images, Videos, PDFs.`);
        return;
      }

      if (isVideo && f.size > 100 * 1024 * 1024) {
        setGalleryError(`Video ${f.name} exceeds maximum size of 100MB.`);
        return;
      }

      if ((isImg || isPdf) && f.size > 10 * 1024 * 1024) {
        setGalleryError(`File ${f.name} exceeds maximum size of 10MB.`);
        return;
      }
    }

    setGalleryFiles((prev) => [...prev, ...newFiles]);
  };

  const removeGalleryFile = (index: number) => {
    setGalleryFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClearPanditForm = () => {
    setPanditFirstName('');
    setPanditLastName('');
    setPanditName('');
    setPanditGender('Male');
    setPanditPhone('');
    setPanditEmail('');
    setPanditCity('');
    setPanditState('');
    setPanditAvailabilityMode('Both');
    setSelectedServiceAreas(['Delhi NCR', 'Online Puja']);
    setPanditServiceAreas('');
    setProfilePhotoPreview(null);
    setPanditExp('5');
    setPanditEducation('');
    setPanditGurukul('');
    setPanditSpec('वैदिक अनुष्ठान (Vedic Rituals)');
    setSelectedSpecs(['वैदिक अनुष्ठान (Vedic Rituals)']);
    setPanditLanguages(['Hindi', 'Sanskrit']);
    setPanditAchievements(['']);
    setPanditBio('');
    setAadhaarFile(null);
    setCertFile(null);
    setGalleryFiles([]);
    setGalleryError(null);
    setPanditPassword('');
    setPanditConfirmPassword('');
    setPanditCodeOfConduct(false);
    setErrors({});
    setPanditStep(1);
    sessionStorage.removeItem('ms_saarthi_pandit_form_data');
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

  const validatePanditStep1 = () => {
    const newErrors: Record<string, string> = {};
    if (!panditFirstName.trim() && !panditName.trim()) {
      newErrors.panditFirstName = 'First name is required.';
    }
    if (!panditLastName.trim() && !panditName.trim()) {
      newErrors.panditLastName = 'Last name is required.';
    }
    if (!panditPhone.trim()) {
      newErrors.panditPhone = 'Mobile number is required.';
    } else if (!/^\+?[0-9\s-]{10,15}$/.test(panditPhone.trim())) {
      newErrors.panditPhone = 'Please enter a valid phone number.';
    }
    if (!panditEmail.trim()) {
      newErrors.panditEmail = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(panditEmail)) {
      newErrors.panditEmail = 'Please enter a valid email address.';
    }
    if (!panditCity.trim()) newErrors.panditCity = 'Primary City is required.';
    if (!panditState.trim()) newErrors.panditState = 'State is required.';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validatePanditStep2 = () => {
    const newErrors: Record<string, string> = {};
    if (!panditExp.trim()) {
      newErrors.panditExp = 'Experience in years is required.';
    }
    if (panditLanguages.length === 0) {
      newErrors.panditLanguages = 'Please select at least one language.';
    }
    if (selectedSpecs.length === 0) {
      newErrors.panditSpec = 'Please select at least one puja specialization.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validatePanditStep3 = () => {
    const newErrors: Record<string, string> = {};
    if (!panditPassword) {
      newErrors.panditPassword = 'Password is required.';
    } else if (panditPassword.length < 8) {
      newErrors.panditPassword = 'Password must be at least 8 characters long.';
    }
    if (panditPassword !== panditConfirmPassword) {
      newErrors.panditConfirmPassword = 'Passwords do not match.';
    }
    if (!panditCodeOfConduct) {
      newErrors.panditCodeOfConduct = 'You must accept the Terms & Conditions and Privacy Policy.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNextStep = (e: React.MouseEvent) => {
    e.preventDefault();
    if (panditStep === 1) {
      if (validatePanditStep1()) setPanditStep(2);
    } else if (panditStep === 2) {
      if (validatePanditStep2()) setPanditStep(3);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (userType === 'pandit') {
      const step1Valid = validatePanditStep1();
      const step2Valid = validatePanditStep2();
      const step3Valid = validatePanditStep3();
      if (!step1Valid) {
        setPanditStep(1);
        return;
      }
      if (!step2Valid) {
        setPanditStep(2);
        return;
      }
      if (!step3Valid) {
        setPanditStep(3);
        return;
      }
    } else {
      if (!validateDevotee()) return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      if (userType === 'pandit') {
        const formData = new FormData();
        const fullName = panditName || `${panditFirstName} ${panditLastName}`.trim() || 'Panditji';
        formData.append('name', fullName);
        formData.append('email', panditEmail);
        formData.append('phone', panditPhone);
        formData.append('password', panditPassword);
        formData.append('confirm_password', panditConfirmPassword);
        formData.append('city', panditCity);
        formData.append('state', panditState);
        formData.append('experience', panditExp.includes('year') ? panditExp : `${panditExp} years`);
        formData.append('gender', panditGender);
        formData.append('availability', panditAvailabilityMode);
        formData.append('education', panditEducation);
        formData.append('gurukul', panditGurukul);
        formData.append('bio', panditBio);

        selectedServiceAreas.forEach((area) => {
          formData.append('service_areas', area);
        });

        panditAchievements.filter((a) => a && a.trim()).forEach((ach) => {
          formData.append('achievements', ach.trim());
        });

        // Format combined specializations into compatible string
        const formattedSpec =
          selectedSpecs.length > 0 ? selectedSpecs.join(', ') : panditSpec;
        formData.append('specialization', formattedSpec);

        panditLanguages.forEach((lang) => {
          formData.append('languages', lang);
        });

        if (aadhaarFile) {
          formData.append('aadhaar_file', aadhaarFile);
        }
        if (certFile) {
          formData.append('certificate_file', certFile);
        }
        if (galleryFiles && galleryFiles.length > 0) {
          galleryFiles.forEach((gf) => {
            formData.append('gallery_files', gf);
          });
        }

        console.log('[FRONTEND-PANDIT-SIGNUP] Sending FormData for Pandit:', fullName, panditEmail);
        const response = await authService.applyPandit(formData);
        console.log('[FRONTEND-PANDIT-SIGNUP] Pandit Apply API response received:', response);

        if (response.status === 'success' || response.application_id) {
          setFormSent(true);
          sessionStorage.removeItem('ms_saarthi_pandit_form_data');

          const firstName = panditFirstName || fullName.split(' ')[0] || 'Panditji';
          const successMsg = `Badhai ho ${firstName} ji! Aapka MantraSetu par Pandit ke roop mein registration safaltapoorvak complete ho gaya hai. Ab aap verified Panditji ke roop mein bhakton ki seva kar sakte hain!`;
          announceMessage(successMsg, true);
        } else {
          throw new Error(response.message || 'Pandit application submission failed.');
        }
      } else {
        console.log('[FRONTEND-DEVOTEE-SIGNUP] Sending signup payload for email:', email);
        const response = await authService.signup({
          user_type: 'devotee',
          name,
          email,
          phone: phone || '9876543210',
          password,
          confirm_password: confirmPassword,
        });

        console.log('[FRONTEND-DEVOTEE-SIGNUP] Signup API response received:', response);

        if (response.status === 'success' || response.user_id || response.access_token) {
          if (response.access_token) {
            login(response.access_token, response.user || { name, email, user_type: 'devotee' });
          }
          setFormSent(true);
          navigate('/', { replace: true });
        }
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Registration failed. Please try again.';
      setErrors({ api: errorMessage });

      if (userType === 'pandit') {
        const errorMsg = 'Lagta hai kuch jaankari mein dikkat hai, kripya form check kariye.';
        announceMessage(errorMsg, false);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <SiteHeader onOpenModal={setModal} />
      <main className="auth-main" data-testid="main-signup">
        <div
          className="auth-wrap"
          style={{
            width: userType === 'pandit' ? 'min(100%, 720px)' : 'min(100%, 460px)',
            transition: 'width 250ms ease',
          }}
        >
          <div className="auth-brand">
            <Link to="/">
              <img src="/mantrasetu-logo.svg" alt="MantraSetu" />
            </Link>
          </div>

          <div className="auth-card" data-testid="card-signup">
            <span className="section-kicker">Join MantraSetu</span>
            <h1>
              {userType === 'pandit'
                ? 'आचार्य-पंडित पंजीकरण प्रपत्र'
                : 'Create your account'}
            </h1>
            <p>
              {userType === 'pandit'
                ? 'Acharya-Pandit Registration Form — Join our certified network of Vedic priests and receive verified ceremony bookings across your region.'
                : 'Book pujas, explore tools and keep your spiritual practice close.'}
            </p>

            {/* Account Type Toggle */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '0.4rem',
                background: '#f3eee8',
                padding: '4px',
                borderRadius: '10px',
                margin: '1.2rem 0 1.5rem 0',
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setUserType('devotee');
                  setErrors({});
                }}
                style={{
                  padding: '0.6rem',
                  borderRadius: '8px',
                  border: 0,
                  fontWeight: 700,
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  background: userType === 'devotee' ? '#fff' : 'transparent',
                  color: userType === 'devotee' ? '#ee7c2b' : '#7a6f64',
                  boxShadow: userType === 'devotee' ? '0 2px 8px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.2s ease',
                }}
                data-testid="tab-user-devotee"
              >
                Devotee Account
              </button>

              <button
                type="button"
                onClick={() => {
                  setUserType('pandit');
                  setErrors({});
                }}
                style={{
                  padding: '0.6rem',
                  borderRadius: '8px',
                  border: 0,
                  fontWeight: 700,
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  background: userType === 'pandit' ? '#fff' : 'transparent',
                  color: userType === 'pandit' ? '#ee7c2b' : '#7a6f64',
                  boxShadow: userType === 'pandit' ? '0 2px 8px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.2s ease',
                }}
                data-testid="tab-user-pandit"
              >
                Panditji Registration
              </button>
            </div>

            {/* Pandit Onboarding Progress Indicator */}
            {userType === 'pandit' && !formSent && (
              <div style={{ marginBottom: '1.8rem' }} data-testid="pandit-wizard-step" data-step={panditStep}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 700, color: '#7a3e1e' }}>
                  <span style={{ color: panditStep >= 1 ? '#ee7c2b' : '#a89d91' }}>1. Personal Information</span>
                  <span style={{ color: panditStep >= 2 ? '#ee7c2b' : '#a89d91' }}>2. Professional Details</span>
                  <span style={{ color: panditStep >= 3 ? '#ee7c2b' : '#a89d91' }}>3. Verification Documents</span>
                </div>
                <div style={{ height: '6px', background: '#f3eee8', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: panditStep === 1 ? '33.3%' : panditStep === 2 ? '66.6%' : '100%',
                      background: 'linear-gradient(90deg, #ee7c2b 0%, #d96620 100%)',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
                <div
                  data-testid="active-field-indicator"
                  style={{
                    marginTop: '0.6rem',
                    padding: '0.5rem 0.8rem',
                    backgroundColor: '#fff7ed',
                    border: '1px solid #ffedd5',
                    borderRadius: '0.5rem',
                    color: '#9a3412',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <span>
                    🎯 Active Question / Field:{' '}
                    <strong style={{ color: '#c2410c' }}>{activeField || '(no active field set)'}</strong>
                  </span>
                  <span style={{ fontSize: '0.75rem', fontWeight: 400, color: '#9a3412', opacity: 0.85 }}>
                    Sync: Step {panditStep} of 3 (Voice &amp; Manual Active)
                  </span>
                </div>
              </div>
            )}

            {formSent ? (
              <div className="form-success" role="status" data-testid="status-signup-success">
                <CheckCircle2 size={24} style={{ color: '#27ae60', flexShrink: 0 }} />
                <div>
                  <strong style={{ fontSize: '1.05rem', color: '#14532d' }}>
                    {userType === 'pandit' ? 'Panditji Application Received!' : 'Welcome to MantraSetu!'}
                  </strong>
                  <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem', color: '#2d5236', lineHeight: 1.5 }}>
                    {userType === 'pandit'
                      ? 'Badhai ho! Our verification team will review your Vedic qualifications and identity documents within 24 hours. You will receive SMS & email confirmation once your profile is verified.'
                      : 'Your devotee account has been created successfully. You can now explore authentic pujas and spiritual tools.'}
                  </p>
                  <Link className="button button-primary" to="/" style={{ marginTop: '1rem', display: 'inline-flex' }}>
                    Return to Homepage
                  </Link>
                </div>
              </div>
            ) : (
              <form
                id={userType === 'pandit' ? 'pandit-onboarding-form' : 'signup-form'}
                className="modal-form"
                onSubmit={handleSubmit}
                noValidate
                data-testid="form-signup"
              >
                {errors.api && (
                  <div
                    className="field-error"
                    role="alert"
                    style={{
                      padding: '0.75rem 1rem',
                      background: '#fdf2f2',
                      border: '1px solid #f8b4b4',
                      borderRadius: '0.5rem',
                      color: '#9b1c1c',
                      fontSize: '0.82rem',
                      marginBottom: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <ShieldAlert size={16} style={{ flexShrink: 0 }} /> {errors.api}
                  </div>
                )}

                {userType === 'pandit' ? (
                  /* ── PANDIT ONBOARDING STEPS ── */
                  <>
                    {/* STEP 1: Personal Information */}
                    {panditStep === 1 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
                        <div style={{ borderBottom: '1px solid #f0e6dc', paddingBottom: '0.5rem' }}>
                          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#3d2b1f' }}>
                            Personal Information (व्यक्तिगत जानकारी)
                          </h3>
                        </div>

                        {/* Profile Photo Upload & Preview */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem', padding: '0.8rem', background: '#faf7f2', borderRadius: '12px', border: '1px solid #efe8e1' }}>
                          <div
                            style={{
                              width: '64px',
                              height: '64px',
                              borderRadius: '50%',
                              background: '#efe8e1',
                              overflow: 'hidden',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              flexShrink: 0,
                            }}
                          >
                            {profilePhotoPreview ? (
                              <img src={profilePhotoPreview} alt="Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            ) : (
                              <User size={30} color="#a08870" />
                            )}
                          </div>
                          <div>
                            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#3d2b1f', display: 'block' }}>फोटो / Profile Photo (Optional)</span>
                            <label style={{ fontSize: '0.78rem', color: '#ee7c2b', fontWeight: 700, cursor: 'pointer', display: 'inline-block', marginTop: '0.2rem' }}>
                              Choose Picture
                              <input
                                id="pandit-avatar"
                                type="file"
                                accept="image/*"
                                style={{ display: 'none' }}
                                onChange={handlePhotoSelect}
                                data-testid="input-pandit-avatar"
                                data-field="pandit-avatar"
                              />
                            </label>
                          </div>
                        </div>

                        {/* First Name & Last Name */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                          <div className="field">
                            <label htmlFor="pandit-first-name">First Name (पहला नाम) *</label>
                            <input
                              id="pandit-first-name"
                              name="firstName"
                              required
                              value={panditFirstName}
                              onChange={(e) => handleFirstNameChange(e.target.value)}
                              placeholder="Enter your first name"
                              data-testid="input-pandit-first-name"
                            />
                            {/* Hidden input keeping backward compatibility with pandit-name testid */}
                            <input
                              id="pandit-name"
                              type="hidden"
                              value={panditName}
                              data-testid="input-pandit-name"
                            />
                            {errors.panditFirstName && (
                              <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditFirstName}</span>
                            )}
                          </div>

                          <div className="field">
                            <label htmlFor="pandit-last-name">Last Name (उपनाम) *</label>
                            <input
                              id="pandit-last-name"
                              name="lastName"
                              required
                              value={panditLastName}
                              onChange={(e) => handleLastNameChange(e.target.value)}
                              placeholder="Enter your last name"
                              data-testid="input-pandit-last-name"
                            />
                            {errors.panditLastName && (
                              <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditLastName}</span>
                            )}
                          </div>
                        </div>

                        {/* Email Address & Phone Number */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                          <div className="field">
                            <label htmlFor="pandit-email">Email Address *</label>
                            <input
                              id="pandit-email"
                              type="email"
                              required
                              value={panditEmail}
                              onChange={(e) => {
                                setPanditEmail(e.target.value);
                                if (errors.panditEmail) clearError('panditEmail');
                              }}
                              placeholder="Enter your email address"
                              data-testid="input-pandit-email"
                            />
                            {errors.panditEmail && (
                              <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditEmail}</span>
                            )}
                          </div>

                          <div className="field">
                            <label htmlFor="pandit-phone">Phone Number (मोबाइल नंबर) *</label>
                            <input
                              id="pandit-phone"
                              type="tel"
                              required
                              value={panditPhone}
                              onChange={(e) => {
                                setPanditPhone(e.target.value);
                                if (errors.panditPhone) clearError('panditPhone');
                              }}
                              placeholder="Enter your phone number"
                              data-testid="input-pandit-phone"
                            />
                            {errors.panditPhone && (
                              <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditPhone}</span>
                            )}
                          </div>
                        </div>

                        {/* Gender & Availability Radio / Pill Groups */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                          <div className="field">
                            <label htmlFor="pandit-gender">Gender *</label>
                            <div data-field="pandit-gender" data-testid="pill-group-pandit-gender" style={{ display: 'flex', gap: '0.4rem', marginTop: '0.2rem' }}>
                              {(['Male', 'Female', 'Other'] as const).map((g) => (
                                <button
                                  key={g}
                                  type="button"
                                  data-testid={`pill-pandit-gender-${g.toLowerCase()}`}
                                  onClick={() => setPanditGender(g)}
                                  style={{
                                    flex: 1,
                                    padding: '0.45rem 0.6rem',
                                    borderRadius: '6px',
                                    border: '1px solid',
                                    borderColor: panditGender === g ? '#ee7c2b' : '#e5d5c1',
                                    background: panditGender === g ? '#fff0e2' : '#fffdf9',
                                    color: panditGender === g ? '#d96620' : '#68645f',
                                    fontSize: '0.82rem',
                                    fontWeight: panditGender === g ? 700 : 500,
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease',
                                  }}
                                >
                                  {g}
                                </button>
                              ))}
                            </div>
                            <select
                              id="pandit-gender"
                              value={panditGender}
                              onChange={(e) => setPanditGender(e.target.value as any)}
                              style={{ display: 'none' }}
                            >
                              <option value="Male">Male</option>
                              <option value="Female">Female</option>
                              <option value="Other">Other</option>
                            </select>
                          </div>

                          <div className="field">
                            <label htmlFor="pandit-availability">Availability *</label>
                            <div data-field="pandit-availability" data-testid="pill-group-pandit-availability" style={{ display: 'flex', gap: '0.4rem', marginTop: '0.2rem' }}>
                              {['Offline', 'Online', 'Both'].map((mode) => (
                                <button
                                  key={mode}
                                  type="button"
                                  data-testid={`pill-pandit-availability-${mode.toLowerCase()}`}
                                  onClick={() => setPanditAvailabilityMode(mode)}
                                  style={{
                                    flex: 1,
                                    padding: '0.45rem 0.6rem',
                                    borderRadius: '6px',
                                    border: '1px solid',
                                    borderColor: panditAvailabilityMode === mode ? '#ee7c2b' : '#e5d5c1',
                                    background: panditAvailabilityMode === mode ? '#fff0e2' : '#fffdf9',
                                    color: panditAvailabilityMode === mode ? '#d96620' : '#68645f',
                                    fontSize: '0.82rem',
                                    fontWeight: panditAvailabilityMode === mode ? 700 : 500,
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease',
                                  }}
                                >
                                  {mode}
                                </button>
                              ))}
                            </div>
                            <input
                              id="pandit-availability"
                              type="hidden"
                              value={panditAvailabilityMode}
                            />
                          </div>
                        </div>

                        {/* Primary City & State */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                          <div className="field">
                            <label htmlFor="pandit-city">Primary City (शहर) *</label>
                            <input
                              id="pandit-city"
                              required
                              value={panditCity}
                              onChange={(e) => {
                                setPanditCity(e.target.value);
                                if (errors.panditCity) clearError('panditCity');
                              }}
                              placeholder="e.g. Varanasi, Haridwar, Delhi"
                              data-testid="input-pandit-city"
                            />
                            {errors.panditCity && (
                              <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditCity}</span>
                            )}
                          </div>

                          <div className="field">
                            <label htmlFor="pandit-state">State (राज्य) *</label>
                            <input
                              id="pandit-state"
                              required
                              value={panditState}
                              onChange={(e) => {
                                setPanditState(e.target.value);
                                if (errors.panditState) clearError('panditState');
                              }}
                              placeholder="e.g. Uttar Pradesh"
                              data-testid="input-pandit-state"
                            />
                            {errors.panditState && (
                              <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditState}</span>
                            )}
                          </div>
                        </div>

                        {/* Service Areas Multi-select Pills & Text */}
                        <div className="field">
                          <label>सेवा क्षेत्र * (Service Areas *)</label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.3rem', marginBottom: '0.5rem' }}>
                            {serviceAreasCatalog.map((area) => {
                              const active = selectedServiceAreas.includes(area);
                              return (
                                <button
                                  key={area}
                                  type="button"
                                  onClick={() => toggleServiceArea(area)}
                                  style={{
                                    padding: '0.3rem 0.65rem',
                                    borderRadius: '6px',
                                    border: '1px solid',
                                    borderColor: active ? '#ee7c2b' : '#e5d5c1',
                                    background: active ? '#fff0e2' : '#fffdf9',
                                    color: active ? '#d96620' : '#68645f',
                                    fontSize: '0.76rem',
                                    fontWeight: active ? 700 : 500,
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease',
                                  }}
                                >
                                  {area} {active ? '✓' : '+'}
                                </button>
                              );
                            })}
                          </div>
                          <input
                            id="pandit-service-areas"
                            value={panditServiceAreas}
                            onChange={(e) => setPanditServiceAreas(e.target.value)}
                            placeholder="Additional operating districts / neighborhoods (e.g. NCR, South Delhi, Noida)"
                            style={{ fontSize: '0.82rem' }}
                          />
                        </div>

                        <button
                          type="button"
                          className="button button-primary"
                          onClick={handleNextStep}
                          style={{ width: '100%', marginTop: '0.4rem', justifyContent: 'center' }}
                          data-testid="button-pandit-next-1"
                        >
                          Next: Professional Details <ArrowRight size={16} />
                        </button>
                      </div>
                    )}

                    {/* STEP 2: Professional Details */}
                    {panditStep === 2 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
                        <div style={{ borderBottom: '1px solid #f0e6dc', paddingBottom: '0.5rem' }}>
                          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#3d2b1f' }}>
                            Professional Details (व्यावसायिक विवरण)
                          </h3>
                        </div>

                        {/* Experience in Years & Education */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                          <div className="field">
                            <label htmlFor="pandit-exp">अनुभव (वर्ष) * (Experience in Years *)</label>
                            <input
                              id="pandit-exp"
                              type="number"
                              min="0"
                              max="60"
                              required
                              value={panditExp}
                              onChange={(e) => {
                                setPanditExp(e.target.value);
                                if (errors.panditExp) clearError('panditExp');
                              }}
                              placeholder="0"
                              data-testid="select-pandit-exp"
                            />
                            {errors.panditExp && (
                              <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditExp}</span>
                            )}
                          </div>

                          <div className="field">
                            <label htmlFor="pandit-gurukul">शिक्षा * (Education *)</label>
                            <input
                              id="pandit-gurukul"
                              value={panditEducation || panditGurukul}
                              onChange={(e) => {
                                setPanditEducation(e.target.value);
                                setPanditGurukul(e.target.value);
                              }}
                              placeholder="Your educational background (e.g. Acharya / Gurukul)"
                            />
                          </div>
                        </div>

                        {/* Languages Spoken */}
                        <div className="field">
                          <label>भाषाएँ * (Languages Known / Speaks *)</label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.3rem' }}>
                            {languagesList.map((lang) => {
                              const active = panditLanguages.includes(lang);
                              return (
                                <button
                                  key={lang}
                                  type="button"
                                  onClick={() => toggleLanguage(lang)}
                                  data-testid={`toggle-lang-${lang.toLowerCase()}`}
                                  style={{
                                    padding: '0.35rem 0.7rem',
                                    borderRadius: '6px',
                                    border: '1px solid',
                                    borderColor: active ? '#ee7c2b' : '#e5d5c1',
                                    background: active ? '#fff0e2' : '#fffdf9',
                                    color: active ? '#d96620' : '#68645f',
                                    fontSize: '0.78rem',
                                    fontWeight: active ? 700 : 500,
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease',
                                  }}
                                >
                                  {lang} {active ? '✓' : '+'}
                                </button>
                              );
                            })}
                          </div>
                          {errors.panditLanguages && (
                            <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditLanguages}</span>
                          )}
                        </div>

                        {/* Specializations Pills */}
                        <div className="field">
                          <label>विशेषज्ञता * (Specialization *)</label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.3rem' }}>
                            {specializationsCatalog.map((spec) => {
                              const active = selectedSpecs.includes(spec);
                              return (
                                <button
                                  key={spec}
                                  type="button"
                                  onClick={() => toggleSpecialization(spec)}
                                  style={{
                                    padding: '0.35rem 0.7rem',
                                    borderRadius: '6px',
                                    border: '1px solid',
                                    borderColor: active ? '#ee7c2b' : '#e5d5c1',
                                    background: active ? '#fff0e2' : '#fffdf9',
                                    color: active ? '#d96620' : '#68645f',
                                    fontSize: '0.78rem',
                                    fontWeight: active ? 700 : 500,
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease',
                                  }}
                                  data-testid={`toggle-spec-${spec.toLowerCase().replaceAll(' ', '-')}`}
                                >
                                  {spec} {active ? '✓' : '+'}
                                </button>
                              );
                            })}
                          </div>
                          {errors.panditSpec && (
                            <span className="field-error" role="alert"><ShieldAlert size={14} /> {errors.panditSpec}</span>
                          )}
                        </div>

                        {/* Dynamic Achievements List */}
                        <div className="field">
                          <label>उपलब्धियां (Achievements)</label>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.3rem' }}>
                            {panditAchievements.map((ach, idx) => (
                              <div key={idx} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                <input
                                  id={idx === 0 ? "pandit-achievements" : `pandit-achievements-${idx}`}
                                  data-testid={`input-pandit-achievements-${idx}`}
                                  value={ach}
                                  onChange={(e) => updateAchievement(idx, e.target.value)}
                                  placeholder={`Achievement ${idx + 1}`}
                                  style={{ flex: 1 }}
                                />
                                {panditAchievements.length > 1 && (
                                  <button
                                    type="button"
                                    onClick={() => removeAchievement(idx)}
                                    style={{
                                      border: '1px solid #f0cfcf',
                                      background: '#fff5f5',
                                      color: '#c53030',
                                      borderRadius: '6px',
                                      padding: '0.5rem',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                    }}
                                    aria-label="Remove achievement"
                                  >
                                    <Trash2 size={16} />
                                  </button>
                                )}
                              </div>
                            ))}
                            <button
                              type="button"
                              onClick={addAchievement}
                              data-testid="button-add-achievement"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                padding: '0.45rem 0.8rem',
                                background: '#ee7c2b',
                                color: '#fff',
                                border: 'none',
                                borderRadius: '6px',
                                fontSize: '0.8rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                alignSelf: 'flex-start',
                                marginTop: '0.2rem',
                              }}
                            >
                              <Plus size={14} /> Add Achievement
                            </button>
                          </div>
                        </div>

                        {/* Bio */}
                        <div className="field">
                          <label htmlFor="pandit-bio">जीवन परिचय * (Bio *)</label>
                          <textarea
                            id="pandit-bio"
                            data-testid="textarea-pandit-bio"
                            value={panditBio}
                            onChange={(e) => setPanditBio(e.target.value)}
                            rows={3}
                            placeholder="Tell us about your spiritual journey, experience, and what makes you unique..."
                            style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '8px', border: '1px solid #d4c5b5', fontSize: '0.85rem' }}
                          />
                        </div>

                        <div style={{ display: 'flex', gap: '0.8rem', marginTop: '0.4rem' }}>
                          <button
                            type="button"
                            className="button button-outline"
                            onClick={() => setPanditStep(1)}
                            style={{ flex: 1, justifyContent: 'center' }}
                          >
                            <ArrowLeft size={15} /> Back
                          </button>
                          <button
                            type="button"
                            className="button button-primary"
                            onClick={handleNextStep}
                            style={{ flex: 2, justifyContent: 'center' }}
                            data-testid="button-pandit-next-2"
                          >
                            Next: Verification Documents <ArrowRight size={15} />
                          </button>
                        </div>
                      </div>
                    )}

                    {/* STEP 3: Verification Documents & Security */}
                    {panditStep === 3 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
                        <div style={{ borderBottom: '1px solid #f0e6dc', paddingBottom: '0.5rem' }}>
                          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#3d2b1f' }}>
                            प्रमाणीकरण दस्तावेज (Verification Documents)
                          </h3>
                        </div>

                        {/* Shiksha Pramanpatra & ID Proof */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                          <div className="field">
                            <label>शिक्षा प्रमाणपत्र (Shiksha Pramanpatra)</label>
                            <label
                              style={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.4rem',
                                padding: '1rem 0.8rem',
                                border: '1px dashed #d99c6b',
                                borderRadius: '10px',
                                background: '#fffaf2',
                                cursor: 'pointer',
                                textAlign: 'center',
                                minHeight: '90px',
                              }}
                            >
                              <Award size={20} color="#d96620" />
                              <span style={{ fontSize: '0.75rem', color: '#7a4b2c', fontWeight: 700 }}>
                                {certFile ? (
                                  <span style={{ color: '#166534', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <FileCheck size={14} /> {certFile.name.slice(0, 16)}...
                                  </span>
                                ) : (
                                  'Upload Certificate'
                                )}
                              </span>
                              <input
                                id="pandit-cert-input"
                                data-testid="input-cert-file"
                                type="file"
                                accept=".pdf,image/*"
                                style={{ display: 'none' }}
                                onChange={(e) => setCertFile(e.target.files?.[0] || null)}
                              />
                            </label>
                          </div>

                          <div className="field">
                            <label>पहचान प्रमाण (ID Proof) *</label>
                            <label
                              style={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.4rem',
                                padding: '1rem 0.8rem',
                                border: '1px dashed #d99c6b',
                                borderRadius: '10px',
                                background: '#fffaf2',
                                cursor: 'pointer',
                                textAlign: 'center',
                                minHeight: '90px',
                              }}
                            >
                              <Upload size={20} color="#d96620" />
                              <span style={{ fontSize: '0.75rem', color: '#7a4b2c', fontWeight: 700 }}>
                                {aadhaarFile ? (
                                  <span style={{ color: '#166534', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <FileCheck size={14} /> {aadhaarFile.name.slice(0, 16)}...
                                  </span>
                                ) : (
                                  'Upload ID Proof / Aadhaar'
                                )}
                              </span>
                              <input
                                id="pandit-aadhaar-input"
                                data-testid="input-aadhaar-file"
                                type="file"
                                accept=".pdf,image/*"
                                style={{ display: 'none' }}
                                onChange={(e) => setAadhaarFile(e.target.files?.[0] || null)}
                              />
                            </label>
                          </div>
                        </div>

                        {/* Gallery - Images & Videos & PDFs */}
                        <div className="field">
                          <label>गैलरी (Gallery) - Images, Videos & PDFs</label>
                          <div
                            style={{
                              border: '1px dashed #d99c6b',
                              borderRadius: '10px',
                              background: '#fffaf2',
                              padding: '0.9rem',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem' }}>
                              <label
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '0.4rem',
                                  padding: '0.45rem 0.8rem',
                                  background: '#ee7c2b',
                                  color: '#fff',
                                  borderRadius: '6px',
                                  fontSize: '0.8rem',
                                  fontWeight: 700,
                                  cursor: 'pointer',
                                }}
                              >
                                <Upload size={14} /> Upload Gallery
                                <input
                                  type="file"
                                  multiple
                                  accept="image/*,video/*,.pdf"
                                  style={{ display: 'none' }}
                                  onChange={handleGallerySelect}
                                />
                              </label>
                              <span style={{ fontSize: '0.74rem', color: '#7a4b2c' }}>
                                Max 7 files. Images (max 10MB), Videos (max 100MB), PDFs (max 10MB)
                              </span>
                            </div>

                            {galleryError && (
                              <div style={{ color: '#9b1c1c', fontSize: '0.75rem', marginTop: '0.4rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <ShieldAlert size={13} /> {galleryError}
                              </div>
                            )}

                            {galleryFiles.length > 0 && (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.7rem' }}>
                                {galleryFiles.map((file, idx) => {
                                  const isVid = file.type.startsWith('video/');
                                  const isPdf = file.type === 'application/pdf';
                                  const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
                                  return (
                                    <div
                                      key={idx}
                                      style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '0.35rem',
                                        background: '#fff',
                                        border: '1px solid #e2d2c1',
                                        borderRadius: '6px',
                                        padding: '0.3rem 0.5rem',
                                        fontSize: '0.74rem',
                                        color: '#3d2b1f',
                                      }}
                                    >
                                      {isVid ? <Film size={13} color="#d96620" /> : isPdf ? <FileText size={13} color="#d96620" /> : <ImageIcon size={13} color="#d96620" />}
                                      <span style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {file.name}
                                      </span>
                                      <span style={{ color: '#8c7b6c', fontSize: '0.7rem' }}>({sizeMb}MB)</span>
                                      <button
                                        type="button"
                                        onClick={() => removeGalleryFile(idx)}
                                        style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 0, color: '#c53030', display: 'flex' }}
                                        aria-label={`Remove ${file.name}`}
                                      >
                                        <X size={13} />
                                      </button>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Password & Confirm */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                          <div className="field">
                            <label htmlFor="pandit-password">Password (पासवर्ड) *</label>
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
                                placeholder="Create a strong password"
                                minLength={8}
                                style={{ paddingRight: '2.8rem' }}
                                aria-invalid={Boolean(errors.panditPassword)}
                                data-testid="input-pandit-password"
                              />
                              <button
                                type="button"
                                onClick={() => setShowPanditPassword((s) => !s)}
                                aria-label={showPanditPassword ? 'Hide password' : 'Show password'}
                                style={{
                                  position: 'absolute',
                                  right: '0.75rem',
                                  top: '50%',
                                  transform: 'translateY(-50%)',
                                  border: 0,
                                  background: 'transparent',
                                  color: '#a08870',
                                  cursor: 'pointer',
                                  padding: 0,
                                }}
                              >
                                {showPanditPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                              </button>
                            </div>
                            <span style={{ fontSize: '0.71rem', color: '#8c7b6c', display: 'block', marginTop: '0.2rem' }}>
                              Min 8 characters with uppercase, lowercase, number, and special character (@$!%*?&#)
                            </span>
                            {errors.panditPassword && (
                              <span className="field-error" role="alert">
                                <ShieldAlert size={14} /> {errors.panditPassword}
                              </span>
                            )}
                          </div>

                          <div className="field">
                            <label htmlFor="pandit-confirm">Confirm Password (पुष्टि करें) *</label>
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
                                placeholder="Confirm your password"
                                style={{ paddingRight: '2.8rem' }}
                                aria-invalid={Boolean(errors.panditConfirmPassword)}
                                data-testid="input-pandit-confirm"
                              />
                              <button
                                type="button"
                                onClick={() => setShowPanditConfirm((s) => !s)}
                                aria-label={showPanditConfirm ? 'Hide confirm password' : 'Show confirm password'}
                                style={{
                                  position: 'absolute',
                                  right: '0.75rem',
                                  top: '50%',
                                  transform: 'translateY(-50%)',
                                  border: 0,
                                  background: 'transparent',
                                  color: '#a08870',
                                  cursor: 'pointer',
                                  padding: 0,
                                }}
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

                        {/* Code of Conduct / Terms Checkbox */}
                        <div className="field">
                          <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.78rem', color: '#68645f', cursor: 'pointer', lineHeight: 1.5 }}>
                            <input
                              type="checkbox"
                              required
                              checked={panditCodeOfConduct}
                              onChange={(e) => {
                                setPanditCodeOfConduct(e.target.checked);
                                if (errors.panditCodeOfConduct) clearError('panditCodeOfConduct');
                              }}
                              style={{ marginTop: '0.15rem', flexShrink: 0 }}
                              data-testid="checkbox-pandit-conduct"
                            />
                            <span>
                              I accept the{' '}
                              <Link to="/terms-of-service" target="_blank" style={{ color: '#d96620', textDecoration: 'none', fontWeight: 700 }}>
                                Terms and Conditions
                              </Link>{' '}
                              and{' '}
                              <Link to="/privacy-policy" target="_blank" style={{ color: '#d96620', textDecoration: 'none', fontWeight: 700 }}>
                                Privacy Policy
                              </Link>{' '}
                              and affirm traditional Vedic ethics and Shastric conduct *.
                            </span>
                          </label>
                          {errors.panditCodeOfConduct && (
                            <span className="field-error" role="alert">
                              <ShieldAlert size={14} /> {errors.panditCodeOfConduct}
                            </span>
                          )}
                        </div>

                        <div style={{ display: 'flex', gap: '0.8rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            className="button button-outline"
                            onClick={() => setPanditStep(2)}
                            style={{ flex: 1, justifyContent: 'center' }}
                          >
                            <ArrowLeft size={15} /> Back
                          </button>
                          <button
                            type="button"
                            onClick={handleClearPanditForm}
                            style={{
                              padding: '0.65rem 1rem',
                              borderRadius: '8px',
                              border: '1px solid #d4c5b5',
                              background: '#fff',
                              color: '#68645f',
                              fontSize: '0.85rem',
                              fontWeight: 700,
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.4rem',
                            }}
                          >
                            <RotateCcw size={14} /> Clear
                          </button>
                          <button
                            className="button button-primary"
                            style={{ flex: 2, minWidth: '180px', justifyContent: 'center' }}
                            type="submit"
                            disabled={isSubmitting}
                            aria-busy={isSubmitting}
                            data-testid="button-submit-pandit-signup"
                          >
                            {isSubmitting ? (
                              <><Loader2 size={16} className="animate-spin" /> Submitting Application...</>
                            ) : (
                              <>Submit <ArrowRight size={15} /></>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  /* ── DEVOTEE REGISTRATION FIELDS ── */
                  <>
                    <div className="field">
                      <label htmlFor="signup-name">Full name *</label>
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
                      <label htmlFor="signup-email">Email address *</label>
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
                      <label htmlFor="signup-password">Password *</label>
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
                          style={{
                            position: 'absolute',
                            right: '0.75rem',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            border: 0,
                            background: 'transparent',
                            color: '#a08870',
                            cursor: 'pointer',
                            padding: 0,
                          }}
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
                      <label htmlFor="signup-confirm">Confirm password *</label>
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
                          style={{
                            position: 'absolute',
                            right: '0.75rem',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            border: 0,
                            background: 'transparent',
                            color: '#a08870',
                            cursor: 'pointer',
                            padding: 0,
                          }}
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
                          <Link to="/terms-of-service" style={{ color: '#d96620', textDecoration: 'none', fontWeight: 700 }}>
                            Terms of Service
                          </Link>{' '}
                          and{' '}
                          <Link to="/privacy-policy" style={{ color: '#d96620', textDecoration: 'none', fontWeight: 700 }}>
                            Privacy Policy
                          </Link>
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
