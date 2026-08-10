import { useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Compass,
  HeartHandshake,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Star,
  TrendingUp,
} from 'lucide-react';
import { SiteHeader, SiteFooter, Modal, FaqAccordion, type ModalType } from '@/components/shared';
import { kundaliService, type KundaliGenerateResponse } from '@/services/kundali.service';

const benefits = [
  {
    id: 'birth-chart',
    icon: Compass,
    title: 'Birth Chart Analysis',
    copy: 'Understand the positions of all nine planets at the time of your birth and their influence on your life.',
  },
  {
    id: 'planetary',
    icon: Star,
    title: 'Planetary Positions',
    copy: 'Detailed insights into each planet\'s house placement and the dasha periods that shape your journey.',
  },
  {
    id: 'career',
    icon: TrendingUp,
    title: 'Career & Finance Guidance',
    copy: 'Discover the houses governing your career, wealth and professional growth through Vedic astrology.',
  },
  {
    id: 'marriage',
    icon: HeartHandshake,
    title: 'Marriage Compatibility',
    copy: 'Explore the seventh house and Venus placements for insights into love, relationships and compatibility.',
  },
];

const faqItems = [
  {
    q: 'What is a Janam Kundali?',
    a: 'A Janam Kundali (birth chart) is a Vedic astrological map of the sky at the exact moment of your birth. It charts the positions of the nine planets across twelve houses and is used to understand your personality, life path and karma.',
  },
  {
    q: 'Why is the exact birth time important?',
    a: 'The ascendant (lagna) and house cusps change roughly every two hours. Even a small difference in birth time can shift planetary placements significantly. The more precise your birth time, the more accurate your kundali will be.',
  },
  {
    q: 'What if I do not know my exact birth time?',
    a: "You can still generate an approximate kundali using sunrise as the default time. However, for detailed predictions, we recommend consulting a panditji who can help rectify the birth time using life events.",
  },
  {
    q: 'Is Vedic astrology different from Western astrology?',
    a: 'Yes. Vedic astrology uses the sidereal zodiac (based on fixed stars) while Western astrology uses the tropical zodiac (based on the Sun\'s position). Vedic astrology also emphasises the Moon sign and ascendant more than the Sun sign.',
  },
  {
    q: 'Can I get a personalised reading?',
    a: 'Absolutely. Once you generate your kundali, you can book a consultation with one of our verified Jyotishi panditjis for a detailed personalised analysis.',
  },
];

export default function KundaliCreation() {
  const [modal, setModal] = useState<ModalType>(null);
  const [formSent, setFormSent] = useState(false);
  const [name, setName] = useState('');
  const [dob, setDob] = useState('');
  const [tob, setTob] = useState('');
  const [pob, setPob] = useState('');
  const [gender, setGender] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [kundaliData, setKundaliData] = useState<KundaliGenerateResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    setApiError(null);

    try {
      const response = await kundaliService.generateKundali({
        name,
        dob,
        tob,
        pob,
        gender,
      });
      setKundaliData(response);
      setFormSent(true);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unable to generate Kundali. Please try again.';
      setApiError(errorMessage);
      setFormSent(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <SiteHeader onOpenModal={setModal} />
      <main>
        {/* ── Hero ── */}
        <section className="tool-hero" aria-labelledby="kundali-title" data-testid="section-kundali-hero">
          <div className="container-wide tool-hero-inner">
            <div className="tool-hero-copy">
              <span className="eyebrow">Your stars hold your story</span>
              <h1 id="kundali-title">Discover your<br /><em>Janam Kundali.</em></h1>
              <p>Generate your personalised Vedic birth chart with accurate planetary positions, house placements and dasha periods.</p>
              <div className="hero-trust">
                <span><ShieldCheck size={15} /> Accurate Vedic calculations</span>
                <span><BookOpen size={15} /> Traditional Jyotish system</span>
              </div>
            </div>
            <div className="tool-hero-mark" aria-hidden="true">
              <div className="tool-orbit tool-orbit-one" />
              <div className="tool-orbit tool-orbit-two" />
              <Star size={52} strokeWidth={1.1} />
            </div>
          </div>
        </section>

        {/* ── Form ── */}
        <section id="kundali-form-section" className="section" aria-labelledby="kundali-form-heading" data-testid="section-kundali-form">
          <div className="container-wide">
            <div className="section-heading">
              <span className="section-kicker">Generate your kundali</span>
              <h2 id="kundali-form-heading">Enter your birth details.</h2>
              <p>Your birth details are used only to calculate your chart. We do not store personal information.</p>
            </div>

            <div className="muhurat-layout">
              <form className="muhurat-form contact-form" onSubmit={handleSubmit} data-testid="form-kundali">
                {apiError && (
                  <div className="field-error" role="alert" style={{ padding: '0.65rem 0.85rem', background: '#fdf2f2', border: '1px solid #f8b4b4', borderRadius: '0.45rem', color: '#9b1c1c', fontSize: '0.78rem', marginBottom: '0.5rem', gridColumn: '1 / -1' }}>
                    <ShieldAlert size={16} style={{ flexShrink: 0 }} /> {apiError}
                  </div>
                )}
                <div className="field field-full">
                  <label htmlFor="kundali-name">Full name</label>
                  <input id="kundali-name" name="name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="As it appears on your birth certificate" data-testid="input-kundali-name" />
                </div>
                <div className="field">
                  <label htmlFor="kundali-dob">Date of birth</label>
                  <input id="kundali-dob" name="dob" type="date" required value={dob} onChange={(e) => setDob(e.target.value)} data-testid="input-kundali-dob" />
                </div>
                <div className="field">
                  <label htmlFor="kundali-tob">Time of birth</label>
                  <input id="kundali-tob" name="tob" type="time" value={tob} onChange={(e) => setTob(e.target.value)} placeholder="HH:MM" data-testid="input-kundali-tob" />
                </div>
                <div className="field field-full">
                  <label htmlFor="kundali-pob">Place of birth</label>
                  <input id="kundali-pob" name="pob" required value={pob} onChange={(e) => setPob(e.target.value)} placeholder="City, State, Country" data-testid="input-kundali-pob" />
                </div>
                <div className="field">
                  <label htmlFor="kundali-gender">Gender</label>
                  <select id="kundali-gender" name="gender" value={gender} onChange={(e) => setGender(e.target.value)} data-testid="select-kundali-gender">
                    <option value="" disabled>Select gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <button className="button button-primary form-submit" type="submit" disabled={isSubmitting} data-testid="button-generate-kundali">
                  {isSubmitting ? (
                    <>
                      <Loader2 size={15} className="animate-spin" /> Generating Kundali...
                    </>
                  ) : (
                    <>
                      Generate Kundali <ArrowRight size={15} />
                    </>
                  )}
                </button>
              </form>

              <div className={`muhurat-results ${formSent ? 'has-results' : ''}`} aria-live="polite" data-testid="kundali-result">
                {!formSent ? (
                  <div className="muhurat-empty">
                    <div className="muhurat-empty-icon"><Star size={22} /></div>
                    <span className="section-kicker">Your kundali will appear here</span>
                    <h3>The stars are waiting for your details.</h3>
                    <p>Enter your birth date, time and place to reveal your personalised Vedic birth chart.</p>
                  </div>
                ) : (
                  <>
                    <div className="muhurat-result-head">
                      <div>
                        <span className="section-kicker">Kundali generated</span>
                        <h3>{kundaliData?.chart_title || (name ? `${name}'s Janam Kundali` : 'Your Janam Kundali is ready.')}</h3>
                      </div>
                      <span className="muhurat-date">Vedic Chart</span>
                    </div>
                    <div className="kundali-chart-placeholder" data-testid="kundali-chart-placeholder">
                      <div className="kundali-chart-grid" aria-label="Vedic birth chart placeholder">
                        {Array.from({ length: 12 }).map((_, i) => {
                          const houseInfo = kundaliData?.houses?.find((h) => h.house === i + 1);
                          return (
                            <div key={i} className="kundali-house">
                              <span className="kundali-house-num">{i + 1}</span>
                              {houseInfo?.sign && (
                                <span style={{ fontSize: '0.62rem', color: '#d96620', fontWeight: 700, display: 'block', marginTop: '0.1rem' }}>
                                  {houseInfo.sign}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      <p className="kundali-chart-note">
                        {kundaliData?.note || 'Full planetary analysis available with a panditji consultation.'}
                      </p>
                    </div>
                    <button className="button button-light muhurat-cta" type="button"
                      onClick={() => setModal('launch')} data-testid="button-book-reading">
                      Book a detailed reading <ArrowRight size={15} />
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* ── Benefits ── */}
        <section className="section section-tint" aria-labelledby="kundali-benefits-heading" data-testid="section-kundali-benefits">
          <div className="container-wide">
            <div className="section-heading centered">
              <span className="section-kicker">What your kundali reveals</span>
              <h2 id="kundali-benefits-heading">Insights from your birth chart</h2>
              <p>Your Janam Kundali is a complete map of the sky at your birth — a guide to understanding your strengths, challenges and purpose.</p>
            </div>
            <div className="service-grid">
              {benefits.map((b) => {
                const Icon = b.icon;
                return (
                  <article className="service-card" key={b.id} data-testid={`card-benefit-${b.id}`}>
                    <div className="service-icon"><Icon size={22} strokeWidth={1.8} /></div>
                    <h3>{b.title}</h3>
                    <p>{b.copy}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── FAQ ── */}
        <section className="section section-tint" aria-labelledby="kundali-faq-heading" data-testid="section-kundali-faq">
          <div className="container-wide">
            <div className="section-heading">
              <span className="section-kicker">Common questions</span>
              <h2 id="kundali-faq-heading">About Kundali Creation</h2>
            </div>
            <FaqAccordion items={faqItems} />
          </div>
        </section>
      </main>
      <SiteFooter />
      <Modal modal={modal} onClose={() => setModal(null)} />
    </div>
  );
}
