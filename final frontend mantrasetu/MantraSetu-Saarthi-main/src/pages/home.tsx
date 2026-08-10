import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  CalendarDays,
  Check,
  Clock3,
  Compass,
  Globe,
  Heart,
  HeartHandshake,
  Lightbulb,
  Loader2,
  Mail,
  MapPin,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Star,
  UsersRound,
  Zap,
} from 'lucide-react';
import { SiteHeader, SiteFooter, Modal, type ModalType } from '@/components/shared';
import contactService from '@/services/contact.service';

const journeyCards: Array<{
  id: string;
  eyebrow: string;
  title: string;
  copy: string;
  href: string;
  modal?: ModalType;
}> = [
  {
    id: 'explore',
    eyebrow: 'Find your way',
    title: 'Explore Spirituality',
    copy: 'Learn, reflect and connect with practices that meet you where you are.',
    href: '#services',
  },
  {
    id: 'puja',
    eyebrow: 'Sacred rituals',
    title: 'Book a Puja',
    copy: 'Bring the blessings of an authentic ritual home, conducted with care.',
    href: '/puja',
  },
  {
    id: 'muhurat',
    eyebrow: 'Auspicious timings',
    title: 'Find Your Muhurat',
    copy: "Discover spiritually favourable moments for life's most meaningful beginnings.",
    href: '/muhurat-finder',
  },
  {
    id: 'pandit',
    eyebrow: 'Trusted guidance',
    title: 'Connect with a Panditji',
    copy: 'Find authentic, verified priests for your ceremonies and sacred occasions.',
    href: '#contact',
  },
];

const services: Array<{
  id: string;
  icon: typeof Sparkles;
  title: string;
  copy: string;
  buttonLabel: string;
  href: string;
  modal?: ModalType;
}> = [
  {
    id: 'puja-booking',
    icon: Sparkles,
    title: 'Puja Booking',
    copy: 'Book authentic pujas with verified panditjis for every important occasion.',
    buttonLabel: 'Book Now',
    href: '/puja',
  },
  {
    id: 'muhurat-finder',
    icon: CalendarDays,
    title: 'Muhurat Finder',
    copy: 'Find auspicious timings for weddings, griha pravesh, business, travel and other important events.',
    buttonLabel: 'Find Muhurat',
    href: '/muhurat-finder',
  },
  {
    id: 'kundali-creation',
    icon: Compass,
    title: 'Kundali Creation',
    copy: 'Generate your Janam Kundali with accurate Vedic astrology insights.',
    buttonLabel: 'Create Kundali',
    href: '/kundali-creation',
  },
  {
    id: 'pandit-consultation',
    icon: UsersRound,
    title: 'Pandit Consultation',
    copy: 'Connect with verified panditjis for rituals, guidance and spiritual consultations.',
    buttonLabel: 'Consult Now',
    href: '#contact',
  },
];

const missionCards = [
  {
    id: 'vision',
    icon: Star,
    title: 'Vision',
    copy: "To become the most trusted digital platform for authentic spiritual services by preserving India's spiritual heritage while making it accessible through modern technology.",
  },
  {
    id: 'mission',
    icon: HeartHandshake,
    title: 'Mission',
    copy: 'To connect devotees with verified panditjis, authentic rituals, Vedic astrology services and AI-powered spiritual guidance through a secure, modern and trustworthy platform.',
  },
];

const coreValues = [
  {
    id: 'authenticity',
    icon: ShieldCheck,
    title: 'Authenticity',
    copy: 'Preserving genuine Vedic traditions and verified spiritual practices.',
  },
  {
    id: 'accessibility',
    icon: Globe,
    title: 'Accessibility',
    copy: 'Making spiritual services available anytime and anywhere.',
  },
  {
    id: 'trust',
    icon: Heart,
    title: 'Trust',
    copy: 'Building transparent relationships between devotees and verified panditjis.',
  },
  {
    id: 'innovation',
    icon: Lightbulb,
    title: 'Innovation',
    copy: 'Using AI and modern technology while preserving tradition.',
  },
  {
    id: 'community',
    icon: UsersRound,
    title: 'Community & Culture',
    copy: 'Promoting Indian heritage and spiritual learning.',
  },
  {
    id: 'devotion',
    icon: Zap,
    title: 'Devotion with Integrity',
    copy: 'Serving every devotee with sincerity, respect and faith.',
  },
];

export default function Home() {
  const [modal, setModal] = useState<ModalType>(null);
  const [formSent, setFormSent] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const openLaunch = () => setModal('launch');

  const handleContactSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setFormSent(false);

    const form = e.currentTarget;
    const formData = new FormData(form);
    const payload = {
      name: (formData.get('name') as string || '').trim(),
      email: (formData.get('email') as string || '').trim(),
      topic: (formData.get('topic') as string || '').trim(),
      message: (formData.get('message') as string || '').trim(),
    };

    try {
      const response = await contactService.sendContactMessage(payload);
      setSuccessMessage(response.message || 'Thank you for reaching out. We will be in touch shortly.');
      setFormSent(true);
      form.reset();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred. Please try again.';
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <SiteHeader page="home" onOpenModal={setModal} />

      <main>
        {/* ── Hero ── */}
        <section className="hero" id="hero-section" aria-labelledby="hero-title" data-testid="section-hero">
          <div className="hero-content">
            <span className="eyebrow">Where Mantras Flow, Divinity Grows</span>
            <h1 id="hero-title">Authentic Pujas.<br /><em>Verified Panditjis.</em><br />Divine Experience.</h1>
            <p className="hero-copy">Where tradition meets trust. Discover meaningful spiritual services, guided by authentic practitioners and designed for the way you live today.</p>
            <div className="hero-actions">
              <button className="button button-primary" type="button" onClick={openLaunch} data-testid="button-book-service">
                Book a Service <ArrowRight size={16} />
              </button>
              <a className="button button-outline" href="#journey" data-testid="link-explore-journey">
                Explore the journey
              </a>
            </div>
            <div className="hero-trust" aria-label="MantraSetu trust signals">
              <span><ShieldCheck size={15} /> Verified panditjis</span>
              <span><HeartHandshake size={15} /> Rituals with care</span>
              <span><Star size={15} /> Rooted in tradition</span>
            </div>
          </div>
        </section>

        {/* ── Begin Your Spiritual Journey ── */}
        <section className="section" id="journey" aria-labelledby="journey-heading" data-testid="section-journey">
          <div className="container-wide">
            <div className="section-heading">
              <span className="section-kicker">Your path, your pace</span>
              <h2 id="journey-heading">Begin Your Spiritual Journey</h2>
              <p>There is no single way to come closer to what matters. Start with a question, a ritual, or a quiet moment for yourself.</p>
            </div>
            <div className="journey-grid">
              {journeyCards.map((card) => (
                <a
                  className="journey-card"
                  href={card.href}
                  onClick={(e) => { if (card.modal) { e.preventDefault(); setModal(card.modal); } }}
                  key={card.id}
                  data-testid={`card-journey-${card.id}`}
                >
                  <div className="journey-content">
                    <span className="eyebrow">{card.eyebrow}</span>
                    <h3>{card.title}</h3>
                    <p>{card.copy}</p>
                    <span className="card-link">Discover more <ArrowRight size={15} /></span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </section>

        {/* ── MantraSetu Special Pujas ── */}
        <section className="section section-tint" id="special-pujas" aria-labelledby="puja-heading" data-testid="section-special-pujas">
          <div className="container-wide">
            <div className="puja-strip">
              <div className="puja-copy">
                <span className="section-kicker">Moments made meaningful</span>
                <h2 id="puja-heading">MantraSetu Special Pujas</h2>
                <p>From new beginnings to heartfelt gratitude, find a ceremony that honours your moment and brings your loved ones together.</p>
                <Link className="button button-light" to="/puja" data-testid="button-view-special-pujas">
                  View Special Pujas <ArrowRight size={15} />
                </Link>
              </div>
              <div className="puja-image" role="img" aria-label="Sacred havan ceremony" data-testid="img-special-puja" />
            </div>
          </div>
        </section>

        {/* ── Our Sacred Services ── */}
        <section className="section" id="services" aria-labelledby="services-heading" data-testid="section-services">
          <div className="container-wide">
            <div className="section-heading centered">
              <span className="section-kicker">A little guidance, when you need it</span>
              <h2 id="services-heading">Our Sacred Services</h2>
              <p>Thoughtful tools and trusted people to help you keep your practice close, wherever life takes you.</p>
            </div>
            <div className="service-grid">
              {services.map((service) => {
                const Icon = service.icon;
                return (
                  <article className="service-card" key={service.id} data-testid={`card-service-${service.id}`}>
                    <div className="service-icon"><Icon size={22} strokeWidth={1.8} /></div>
                    <h3>{service.title}</h3>
                    <p>{service.copy}</p>
                    <div className="service-footer">
                      <a
                        className="text-action"
                        href={service.href}
                        onClick={(e) => {
                          if (service.modal) {
                            e.preventDefault();
                            setModal(service.modal);
                          }
                        }}
                        data-testid={`button-service-${service.id}`}
                      >
                        {service.buttonLabel} <ArrowRight size={14} />
                      </a>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── Our Sacred Mission ── */}
        <section className="section section-tint" id="mission" aria-labelledby="mission-heading" data-testid="section-mission">
          <div className="container-wide">
            <div className="section-heading centered">
              <span className="section-kicker">Who we are</span>
              <h2 id="mission-heading">Our Sacred Mission</h2>
              <p>We exist to bridge the timeless wisdom of India's spiritual heritage with the needs of the modern devotee.</p>
            </div>
            <div className="mission-grid">
              {missionCards.map((card) => {
                const Icon = card.icon;
                return (
                  <article className="service-card mission-card" key={card.id} data-testid={`card-mission-${card.id}`}>
                    <div className="service-icon"><Icon size={22} strokeWidth={1.8} /></div>
                    <h3>{card.title}</h3>
                    <p>{card.copy}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── Core Philosophy ── */}
        <section className="section" id="philosophy" aria-labelledby="philosophy-heading" data-testid="section-philosophy">
          <div className="container-wide">
            <div className="philosophy-block">
              <span className="section-kicker">Our guiding principle</span>
              <h2 id="philosophy-heading" className="visually-hidden">Core Philosophy</h2>
              <blockquote className="philosophy-quote">
                "Blending authenticity, technology and devotion to make spirituality accessible and meaningful for everyone."
              </blockquote>
            </div>
          </div>
        </section>

        {/* ── Our Core Values ── */}
        <section className="section section-tint" id="values" aria-labelledby="values-heading" data-testid="section-values">
          <div className="container-wide">
            <div className="section-heading centered">
              <span className="section-kicker">What drives us</span>
              <h2 id="values-heading">Our Core Values</h2>
              <p>Every decision we make is grounded in these six principles that guide our team and platform.</p>
            </div>
            <div className="values-grid">
              {coreValues.map((value) => {
                const Icon = value.icon;
                return (
                  <article className="service-card" key={value.id} data-testid={`card-value-${value.id}`}>
                    <div className="service-icon"><Icon size={22} strokeWidth={1.8} /></div>
                    <h3>{value.title}</h3>
                    <p>{value.copy}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── Become a Pandit ── */}
        <section className="section" id="become-a-pandit" aria-labelledby="pandit-cta-heading" data-testid="section-become-pandit">
          <div className="container-wide">
            <div className="puja-strip" style={{ background: 'linear-gradient(135deg, #3d2118 0%, #653820 54%, #7a4829 100%)' }}>
              <div className="puja-copy">
                <span className="section-kicker">Join our network</span>
                <h2 id="pandit-cta-heading">Become a Pandit</h2>
                <p>Are you a practising Vedic priest or astrologer? Join the MantraSetu network to expand your reach, manage ceremony bookings digitally, and connect with devotees across India.</p>
                <div style={{ display: 'grid', gap: '0.6rem', margin: '1rem 0 1.5rem', color: 'rgba(255,245,228,0.85)', fontSize: '0.82rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ShieldCheck size={16} color="#ffc477" /> Direct & transparent ceremony bookings
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <UsersRound size={16} color="#ffc477" /> Connect with faithful families seeking authentic rituals
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Sparkles size={16} color="#ffc477" /> Flexible scheduling & location preferences
                  </div>
                </div>
                <Link className="button button-light" to="/sign-up?role=pandit" data-testid="button-become-pandit-cta">
                  Become a Pandit <ArrowRight size={15} />
                </Link>
              </div>
              <div className="puja-image" style={{ backgroundImage: 'url("/journey-pandit.jpg")' }} role="img" aria-label="Verified Panditji performing ritual" data-testid="img-become-pandit" />
            </div>
          </div>
        </section>

        {/* ── Contact ── */}
        <section className="section" id="contact" aria-labelledby="contact-heading" data-testid="section-contact">
          <div className="container-wide contact-wrap">
            <div className="contact-intro">
              <span className="section-kicker">We would love to hear from you</span>
              <h2 id="contact-heading">Get in Touch</h2>
              <p>Have a question about a ritual, a service, or what is coming next? Leave us a note and our team will be in touch.</p>
              <div className="contact-details">
                <div className="contact-detail"><MapPin size={18} /><span>New Delhi, India<br />Serving seekers everywhere</span></div>
                <div className="contact-detail"><Mail size={18} /><span>hello@mantrasetu.com</span></div>
                <div className="contact-detail"><Clock3 size={18} /><span>Monday – Saturday<br />10:00 AM – 6:00 PM IST</span></div>
              </div>
            </div>
            <form className="contact-form" onSubmit={handleContactSubmit} data-testid="form-contact">
              {error && (
                <div className="field-error" role="alert" data-testid="status-contact-error" style={{ padding: '0.65rem 0.85rem', background: '#fdf2f2', border: '1px solid #f8b4b4', borderRadius: '0.45rem', color: '#9b1c1c', fontSize: '0.78rem', marginBottom: '0.5rem', gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ShieldAlert size={16} style={{ flexShrink: 0 }} /> {error}
                </div>
              )}
              {formSent && (
                <div className="form-success" role="status" data-testid="status-contact-success">
                  <Check size={15} /> {successMessage || 'Thank you for reaching out. We will be in touch shortly.'}
                </div>
              )}
              <div className="field">
                <label htmlFor="contact-name">Your name</label>
                <input id="contact-name" name="name" required placeholder="How should we address you?" data-testid="input-contact-name" />
              </div>
              <div className="field">
                <label htmlFor="contact-email">Email address</label>
                <input id="contact-email" name="email" type="email" required placeholder="you@example.com" data-testid="input-contact-email" />
              </div>
              <div className="field field-full">
                <label htmlFor="contact-topic">I am curious about</label>
                <select id="contact-topic" name="topic" defaultValue="" data-testid="select-contact-topic">
                  <option value="" disabled>Select a topic</option>
                  <option value="puja">Booking a puja</option>
                  <option value="services">Sacred services</option>
                  <option value="saarthi">Saarthi assistant</option>
                  <option value="other">Something else</option>
                </select>
              </div>
              <div className="field field-full">
                <label htmlFor="contact-message">Your message</label>
                <textarea id="contact-message" name="message" required placeholder="Tell us a little about what is on your mind..." data-testid="textarea-contact-message" />
              </div>
              <button className="button button-primary form-submit" type="submit" disabled={isSubmitting} data-testid="button-submit-contact">
                {isSubmitting ? (
                  <>
                    <Loader2 size={15} className="animate-spin" /> Sending...
                  </>
                ) : (
                  <>
                    Send message <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>
          </div>
        </section>
      </main>

      <SiteFooter />
      <Modal modal={modal} onClose={() => setModal(null)} />
    </div>
  );
}
