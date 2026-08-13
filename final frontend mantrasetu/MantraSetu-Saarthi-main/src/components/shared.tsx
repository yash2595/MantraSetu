import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  ArrowRight,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Menu,
  Search,
  ShieldCheck,
  User,
  X,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { authService } from '@/services/auth.service';

export type ModalType = 'signup' | 'login' | 'launch' | 'assistant' | null;

export const primaryNavItems = {
  services: [
    { label: 'Book Puja', href: '/puja' },
    { label: 'Astrology', href: '/kundali-creation' },
    { label: 'Havan', href: '/puja' },
    { label: 'Katha', href: '/puja' },
    { label: 'Special Occasions', href: '/puja' },
    { label: 'Pandit Consultation', href: '/#contact' },
  ],
  spiritualTools: [
    { label: 'Panchang', href: '/muhurat-finder' },
    { label: 'Muhurat Finder', href: '/muhurat-finder' },
    { label: 'Rashifal', href: '/kundali-creation' },
    { label: 'Kundali', href: '/kundali-creation' },
    { label: 'Gemstone Guide', href: '/kundali-creation' },
    { label: 'Choghadiya', href: '/muhurat-finder' },
  ],
};

const searchCatalog = [
  { label: 'Puja Booking', href: '/puja', source: 'Book authentic pujas with verified panditjis for every occasion.' },
  { label: 'Muhurat Finder', href: '/muhurat-finder', source: 'Find auspicious timings for weddings, griha pravesh and other events.' },
  { label: 'Kundali Creation', href: '/kundali-creation', source: 'Generate your Janam Kundali with Vedic astrology insights.' },
  { label: 'Pandit Consultation', href: '/#contact', source: 'Connect with verified panditjis for rituals and guidance.' },
  { label: 'Rashifal', href: '/kundali-creation', source: 'Daily, weekly and monthly horoscope for all zodiac signs.' },
  { label: 'Panchang', href: '/muhurat-finder', source: "Today's panchang with tithi, nakshatra, yoga and auspicious timings." },
  { label: 'Choghadiya', href: '/muhurat-finder', source: 'Day and night choghadiya for auspicious muhurat timings.' },
  { label: 'Gemstone Guide', href: '/kundali-creation', source: 'Vedic gemstone recommendations by zodiac sign and planet.' },
  { label: 'Contact', href: '/#contact', source: 'Get in touch with the MantraSetu team.' },
  { label: 'Special Pujas', href: '/puja', source: 'Ceremonies for meaningful moments and special occasions.' },
  { label: 'Pandit Onboarding', href: '/sign-up?role=pandit', source: 'Join the MantraSetu network as a verified panditji.' },
  { label: 'Login', href: '/login', source: 'Sign in to your MantraSetu account.' },
  { label: 'Sign Up', href: '/sign-up', source: 'Create a MantraSetu account.' },
];

export function SiteHeader({
  page,
  onOpenModal,
}: {
  page?: string;
  onOpenModal?: (modal: ModalType) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const { isAuthenticated, logout } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [scrolled, setScrolled] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<'services' | 'spiritual-tools' | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const searchResults = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return [];
    return searchCatalog.filter((item) => `${item.label} ${item.source}`.toLowerCase().includes(query));
  }, [searchTerm]);

  const closeNavigation = () => {
    setMenuOpen(false);
    setSearchOpen(false);
    setActiveDropdown(null);
  };

  const handleNavClick = (e: React.MouseEvent, item: { href: string; modal?: ModalType }) => {
    closeNavigation();
    if (item.modal && onOpenModal) {
      if (window.location.pathname === '/' || window.location.pathname === '') {
        e.preventDefault();
        onOpenModal(item.modal);
      }
    }
  };

  const isHome = page === 'home';
  const homeHref = isHome ? '#home' : '/';
  const contactHref = isHome ? '#contact' : '/#contact';

  const renderLink = (href: string, className: string, children: React.ReactNode, extraProps: Record<string, any> = {}) => {
    if (href.startsWith('#') || href.startsWith('/#')) {
      return (
        <a href={href} className={className} {...extraProps}>
          {children}
        </a>
      );
    }
    return (
      <Link to={href} className={className} {...extraProps}>
        {children}
      </Link>
    );
  };

  return (
    <>
      <header className={`site-header ${scrolled ? 'scrolled' : ''}`} data-testid="site-header">
        <div className="container-wide header-inner">
          {renderLink(homeHref, 'brand-link', <img className="brand-mark" src="/mantrasetu-logo.svg" alt="MantraSetu" data-testid="img-mantrasetu-logo" />, { onClick: closeNavigation, 'data-testid': 'link-home-logo' })}

          <nav className="nav-links" aria-label="Primary navigation">
            {renderLink(homeHref, 'nav-link', 'Home', { onClick: closeNavigation, 'data-testid': 'link-nav-home' })}
            <div
              className={`nav-dropdown ${activeDropdown === 'services' ? 'open' : ''}`}
              onMouseEnter={() => setActiveDropdown('services')}
              onMouseLeave={() => setActiveDropdown(null)}
            >
              <button
                className="nav-link nav-menu-trigger"
                type="button"
                aria-expanded={activeDropdown === 'services'}
                aria-haspopup="true"
                onClick={() => setActiveDropdown(activeDropdown === 'services' ? null : 'services')}
                data-testid="button-nav-services"
              >
                Services <ChevronDown size={13} />
              </button>
              <div className="nav-dropdown-menu" role="menu">
                {primaryNavItems.services.map((item) => (
                  renderLink(
                    item.href,
                    '',
                    item.label,
                    {
                      role: 'menuitem',
                      key: item.label,
                      onClick: (e: React.MouseEvent) => handleNavClick(e, item),
                      'data-testid': `link-nav-service-${item.label.toLowerCase().replaceAll(' ', '-')}`,
                    }
                  )
                ))}
              </div>
            </div>
            <div
              className={`nav-dropdown ${activeDropdown === 'spiritual-tools' ? 'open' : ''}`}
              onMouseEnter={() => setActiveDropdown('spiritual-tools')}
              onMouseLeave={() => setActiveDropdown(null)}
            >
              <button
                className="nav-link nav-menu-trigger"
                type="button"
                aria-expanded={activeDropdown === 'spiritual-tools'}
                aria-haspopup="true"
                onClick={() => setActiveDropdown(activeDropdown === 'spiritual-tools' ? null : 'spiritual-tools')}
                data-testid="button-nav-spiritual-tools"
              >
                Spiritual Tools <ChevronDown size={13} />
              </button>
              <div className="nav-dropdown-menu" role="menu">
                {primaryNavItems.spiritualTools.map((item) => (
                  renderLink(
                    item.href,
                    '',
                    item.label,
                    {
                      role: 'menuitem',
                      key: item.label,
                      onClick: closeNavigation,
                      'data-testid': `link-nav-tool-${item.label.toLowerCase().replaceAll(' ', '-')}`,
                    }
                  )
                ))}
              </div>
            </div>
            {renderLink(contactHref, 'nav-link', 'Contact', { onClick: closeNavigation, 'data-testid': 'link-nav-contact' })}
          </nav>

          <div className="header-actions">
            <button className="icon-button" type="button" aria-label="Search MantraSetu"
              onClick={() => setSearchOpen((o) => !o)} data-testid="button-open-search">
              <Search size={17} strokeWidth={2.3} />
            </button>
            {isAuthenticated ? (
              <button className="button button-outline" onClick={() => logout()} data-testid="button-logout">Logout</button>
            ) : (
              <>
                <Link className="button button-outline" to="/login" data-testid="button-login">Login</Link>
                <Link className="button button-primary" to="/sign-up" data-testid="button-signup">Sign Up</Link>
              </>
            )}
            <Link
              className="button button-outline"
              style={{ padding: '0.4rem' }}
              aria-label="Account Settings"
              to={isAuthenticated ? "/dashboard" : "/login"}
              data-testid="button-account-settings"
            >
              Book Puja
            </Link>
            <button className="menu-button mobile-only" type="button"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen}
              onClick={() => setMenuOpen((o) => !o)} data-testid="button-mobile-menu">
              {menuOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
          </div>
        </div>

        <div className={`mobile-menu ${menuOpen ? 'open' : ''}`} data-testid="mobile-navigation">
          {renderLink(homeHref, '', 'Home', { onClick: closeNavigation, 'data-testid': 'link-mobile-home' })}
          <div className="mobile-menu-group">
            <button className="mobile-menu-group-trigger" type="button"
              aria-expanded={activeDropdown === 'services'}
              onClick={() => setActiveDropdown(activeDropdown === 'services' ? null : 'services')}
              data-testid="button-mobile-services">
              Services <ChevronDown size={15} />
            </button>
            {activeDropdown === 'services' && (
              <div className="mobile-submenu">
                {primaryNavItems.services.map((item) => (
                  renderLink(item.href, '', item.label, { onClick: (e: React.MouseEvent) => handleNavClick(e, item), key: item.label })
                ))}
              </div>
            )}
          </div>
          <div className="mobile-menu-group">
            <button className="mobile-menu-group-trigger" type="button"
              aria-expanded={activeDropdown === 'spiritual-tools'}
              onClick={() => setActiveDropdown(activeDropdown === 'spiritual-tools' ? null : 'spiritual-tools')}
              data-testid="button-mobile-spiritual-tools">
              Spiritual Tools <ChevronDown size={15} />
            </button>
            {activeDropdown === 'spiritual-tools' && (
              <div className="mobile-submenu">
                {primaryNavItems.spiritualTools.map((item) => (
                  renderLink(item.href, '', item.label, { onClick: closeNavigation, key: item.label })
                ))}
              </div>
            )}
          </div>
          {renderLink(contactHref, '', 'Contact', { onClick: closeNavigation, 'data-testid': 'link-mobile-contact' })}
          <Link className="button button-primary" to="/puja" onClick={closeNavigation} data-testid="button-mobile-book-puja">
            Book a Puja <ArrowRight size={15} />
          </Link>
        </div>
      </header>

      <div className={`search-panel ${searchOpen ? 'open' : ''}`} role="search" data-testid="search-panel">
        <div className="container-wide">
          <div className="search-form">
            <Search size={17} color="#bd6930" aria-hidden="true" />
            <input
              type="search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search services, pujas and spiritual tools"
              aria-label="Search services, pujas and spiritual tools"
              autoFocus={searchOpen}
              data-testid="input-search"
            />
            <button className="icon-button" type="button" aria-label="Close search"
              onClick={() => { setSearchOpen(false); setSearchTerm(''); }} data-testid="button-close-search">
              <X size={16} />
            </button>
          </div>
          {searchTerm && searchResults.length > 0 && (
            <div className="search-results" data-testid="search-results">
              {searchResults.map((result) => (
                renderLink(
                  result.href,
                  'search-result',
                  <>{result.label} <ChevronRight size={13} /></>,
                  {
                    onClick: closeNavigation,
                    key: result.label,
                    'data-testid': `link-search-${result.label.toLowerCase().replaceAll(' ', '-')}`,
                  }
                )
              ))}
            </div>
          )}
          {searchTerm && searchResults.length === 0 && (
            <p className="search-empty" data-testid="text-search-empty">
              No results found. Try "puja", "kundali" or "muhurat".
            </p>
          )}
        </div>
      </div>
    </>
  );
}

export function SiteFooter() {
  return (
    <footer className="footer" data-testid="site-footer">
      <div className="container-wide">
        <div className="footer-top">
          <img src="/mantrasetu-logo.svg" alt="MantraSetu" className="footer-brand" data-testid="img-footer-logo" />
          <p>Where mantras flow, divinity grows. A trusted home for spiritual services, guidance and connection.</p>
        </div>
        <nav className="footer-nav" aria-label="Footer navigation">
          <Link to="/">Home</Link>
          <Link to="/puja">Book Puja</Link>
          <Link to="/muhurat-finder">Muhurat Finder</Link>
          <Link to="/kundali-creation">Kundali</Link>
          <Link to="/kundali-creation">Rashifal</Link>
          <Link to="/muhurat-finder">Panchang</Link>
          <Link to="/kundali-creation">Gemstone Guide</Link>
          <Link to="/muhurat-finder">Choghadiya</Link>
          <a href="/#contact">Contact</a>
          <div className="footer-links">
            <Link to="/sign-up?role=pandit">Pandit Registration</Link>
            <Link to="/puja">Special Pujas</Link>
          </div>
        </nav>
        <div className="footer-bottom">
          <span>© 2025 MantraSetu. Rooted in faith, made with care.</span>
          <span>Privacy · Terms</span>
        </div>
      </div>
    </footer>
  );
}

export function Modal({ modal, onClose }: { modal: ModalType; onClose: () => void }) {
  if (!modal) return null;
  const isAssistant = modal === 'assistant';
  const isLogin = modal === 'login';
  const isSignup = modal === 'signup';

  const [modalName, setModalName] = useState('');
  const [modalEmail, setModalEmail] = useState('');
  const [modalPassword, setModalPassword] = useState('');
  const [modalError, setModalError] = useState('');
  const [modalSubmitting, setModalSubmitting] = useState(false);
  const { login } = useAuth();

  const handleModalAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError('');
    setModalSubmitting(true);
    console.log(`[FRONTEND-MODAL] Submitting ${isLogin ? 'Login' : 'Signup'} for email: ${modalEmail}`);
    try {
      if (isLogin) {
        const res = await authService.login({ email: modalEmail, password: modalPassword });
        console.log('[FRONTEND-MODAL] Login API response:', res);
        if (res.access_token) {
          login(res.access_token, res.user);
          onClose();
        }
      } else if (isSignup) {
        const res = await authService.signup({
          name: modalName,
          email: modalEmail,
          phone: '9876543210',
          password: modalPassword,
          confirm_password: modalPassword,
        });
        console.log('[FRONTEND-MODAL] Signup API response:', res);
        if (res.access_token) {
          login(res.access_token, res.user || { name: modalName, email: modalEmail });
        }
        onClose();
      }
    } catch (err: any) {
      console.error('[FRONTEND-MODAL] Error during auth API call:', err);
      setModalError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setModalSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop open" role="presentation"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
      data-testid="modal-backdrop">
      <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-title"
        data-testid={`modal-${modal}`}>
        <button className="modal-close" type="button" onClick={onClose} aria-label="Close dialog"
          data-testid="button-close-modal"><X size={16} /></button>
        {isAssistant ? (
          <>
            <span className="section-kicker">Your spiritual companion</span>
            <h2 id="modal-title">Saarthi is finding its way to you.</h2>
            <p>We are preparing a thoughtful AI guide for everyday spiritual questions and practices.</p>
            <div className="modal-note"><CircleHelp size={18} /> In the meantime, tell us what you would love Saarthi to help with.</div>
            <form className="modal-form" onSubmit={(e) => { e.preventDefault(); onClose(); }} style={{ marginTop: '1rem' }}>
              <div className="field"><label htmlFor="saarthi-q">What is on your mind?</label>
                <textarea id="saarthi-q" required placeholder="Ask a question or share an idea..." /></div>
              <button className="button button-primary" type="submit">Share with Saarthi <ArrowRight size={15} /></button>
            </form>
          </>
        ) : isLogin || isSignup ? (
          <>
            <span className="section-kicker">A sacred space for you</span>
            <h2 id="modal-title">{isLogin ? 'Welcome back to MantraSetu.' : 'Begin your journey with us.'}</h2>
            <p>{isLogin ? 'Sign in to keep your rituals and spiritual moments close.' : 'Create your space to save services, explore rituals and stay connected.'}</p>
            {modalError && (
              <div className="modal-note" style={{ backgroundColor: '#fef2f2', borderColor: '#fca5a5', color: '#991b1b', marginBottom: '1rem' }}>
                {modalError}
              </div>
            )}
            <form className="modal-form" onSubmit={handleModalAuthSubmit}>
              {!isLogin && <div className="field"><label htmlFor="modal-name">Your name</label>
                <input id="modal-name" value={modalName} onChange={(e) => setModalName(e.target.value)} required placeholder="Your name" /></div>}
              <div className="field"><label htmlFor="modal-email">Email address</label>
                <input id="modal-email" type="email" value={modalEmail} onChange={(e) => setModalEmail(e.target.value)} required placeholder="you@example.com" /></div>
              <div className="field"><label htmlFor="modal-password">Password</label>
                <input id="modal-password" type="password" value={modalPassword} onChange={(e) => setModalPassword(e.target.value)} required placeholder="Enter your password" /></div>
              <button className="button button-primary" type="submit" disabled={modalSubmitting}>
                {modalSubmitting ? 'Please wait...' : (isLogin ? 'Continue' : 'Create account')} <ArrowRight size={15} />
              </button>
            </form>
          </>
        ) : (
          <>
            <span className="section-kicker">Coming soon</span>
            <h2 id="modal-title">A beautiful ritual, made easy.</h2>
            <p>Our booking experience is being prepared with the same care as the ceremonies it holds. Leave your email and we will let you know when it opens.</p>
            <form className="modal-form" onSubmit={(e) => { e.preventDefault(); onClose(); }}>
              <div className="field"><label htmlFor="launch-email">Email address</label>
                <input id="launch-email" type="email" required placeholder="you@example.com" /></div>
              <button className="button button-primary" type="submit">Keep me posted <ArrowRight size={15} /></button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

export function SunriseIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v4M4.93 6.93l2.83 2.83M3 14h4M17 14h4M16.24 9.76l2.83-2.83M5 18h14" />
      <path d="M8 14a4 4 0 0 1 8 0" />
    </svg>
  );
}

export function FaqAccordion({ items }: { items: { q: string; a: string }[] }) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  return (
    <div className="faq-accordion">
      {items.map((item, i) => (
        <div key={i} className={`faq-item ${openIdx === i ? 'open' : ''}`}>
          <button className="faq-question" type="button" aria-expanded={openIdx === i}
            onClick={() => setOpenIdx(openIdx === i ? null : i)}>
            {item.q}
            <ChevronDown size={16} />
          </button>
          {openIdx === i && <div className="faq-answer"><p>{item.a}</p></div>}
        </div>
      ))}
    </div>
  );
}
