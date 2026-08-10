import { useState } from 'react';
import {
  ArrowRight,
  CalendarDays,
  Check,
  CircleHelp,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Star,
} from 'lucide-react';
import { SiteHeader, SiteFooter, Modal, SunriseIcon, FaqAccordion, type ModalType } from '@/components/shared';
import { muhuratService, type TimingCardItem } from '@/services/muhurat.service';

const faqItems = [
  {
    q: 'What is a Muhurat?',
    a: 'A Muhurat is an auspicious time period traditionally calculated using Hindu panchang (almanac) for beginning important activities like weddings, griha pravesh, business openings and other significant events.',
  },
  {
    q: 'How are these timings calculated?',
    a: 'Timings are based on traditional Vedic panchang calculations that consider the tithi (lunar day), nakshatra (star), yoga, karana and local sunrise/sunset times for the selected city.',
  },
  {
    q: 'Can I trust these timings for my ceremony?',
    a: 'These are traditional reference timings. For personal ceremonies, we always recommend confirming with a qualified panditji who can consider your specific kundali and family traditions.',
  },
  {
    q: 'Why does location matter?',
    a: 'Sunrise, sunset and local panchang timings differ by city. The Muhurat is calculated based on the local astronomical conditions of your chosen location.',
  },
  {
    q: 'Are there any timings I should avoid?',
    a: 'Traditionally, Rahu Kaal, Yamaghantam and Gulika Kaal are considered inauspicious and should be avoided for new beginnings. These are shown separately in the full panchang view.',
  },
];

export default function MuhuratFinder() {
  const [modal, setModal] = useState<ModalType>(null);
  const [eventType, setEventType] = useState('griha-pravesh');
  const [city, setCity] = useState('new-delhi');
  const [date, setDate] = useState('2026-08-12');
  const [searched, setSearched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [backendTimings, setBackendTimings] = useState<TimingCardItem[] | null>(null);

  const handleSearch = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    setApiError(null);

    try {
      const response = await muhuratService.findMuhurat({
        event_type: eventType,
        city,
        date,
      });

      if (response.timings && response.timings.length > 0) {
        setBackendTimings(response.timings);
      } else {
        setBackendTimings(null);
      }
      setSearched(true);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unable to calculate Muhurat. Please try again.';
      setApiError(errorMessage);
      setSearched(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const eventLabel =
    eventType === 'griha-pravesh' ? 'Griha Pravesh'
    : eventType === 'vivah' ? 'Vivah Sanskar'
    : eventType === 'naamkaran' ? 'Naamkaran'
    : 'Business Opening';

  const cityLabel =
    city === 'new-delhi' ? 'New Delhi'
    : city === 'mumbai' ? 'Mumbai'
    : city === 'bengaluru' ? 'Bengaluru'
    : 'Jaipur';

  const displayTimings = backendTimings || [
    {
      label: 'Most auspicious',
      time_range: '06:18 AM – 07:54 AM',
      description: 'Brahma Muhurat · A peaceful window for a sacred start',
      is_featured: true,
    },
    {
      label: 'Morning window',
      time_range: '09:42 AM – 11:16 AM',
      description: 'Favourable for preparations and first steps',
      is_featured: false,
    },
    {
      label: 'Evening window',
      time_range: '04:32 PM – 06:08 PM',
      description: 'A gentle closing window before sunset',
      is_featured: false,
    },
  ];

  return (
    <div className="page-shell">
      <SiteHeader onOpenModal={setModal} />
      <main>
        {/* ── Hero ── */}
        <section className="tool-hero" aria-labelledby="muhurat-title" data-testid="section-muhurat-hero">
          <div className="container-wide tool-hero-inner">
            <div className="tool-hero-copy">
              <span className="eyebrow">Auspicious beginnings, thoughtfully timed</span>
              <h1 id="muhurat-title">Find a moment<br /><em>that feels right.</em></h1>
              <p>Discover auspicious timings for the occasions that matter. Begin with your purpose, place and preferred date.</p>
              <div className="hero-trust" aria-label="Muhurat Finder benefits">
                <span><CalendarDays size={15} /> Traditional calculations</span>
                <span><ShieldCheck size={15} /> Clear and considered</span>
              </div>
            </div>
            <div className="tool-hero-mark" aria-hidden="true">
              <div className="tool-orbit tool-orbit-one" />
              <div className="tool-orbit tool-orbit-two" />
              <Sparkles size={52} strokeWidth={1.1} />
            </div>
          </div>
        </section>

        {/* ── Finder ── */}
        <section id="muhurat-finder-section" className="section muhurat-section" aria-labelledby="finder-heading" data-testid="section-muhurat-finder">
          <div className="container-wide">
            <div className="section-heading">
              <span className="section-kicker">Muhurat Finder</span>
              <h2 id="finder-heading">Choose what you are beginning.</h2>
              <p>Every occasion carries its own rhythm. Tell us a little about yours and we will show you the moments traditionally considered most supportive.</p>
            </div>

            <div className="muhurat-layout">
              <form className="muhurat-form contact-form" onSubmit={handleSearch} data-testid="form-muhurat-finder">
                {apiError && (
                  <div className="field-error" role="alert" style={{ padding: '0.65rem 0.85rem', background: '#fdf2f2', border: '1px solid #f8b4b4', borderRadius: '0.45rem', color: '#9b1c1c', fontSize: '0.78rem', marginBottom: '0.5rem', gridColumn: '1 / -1' }}>
                    <ShieldAlert size={16} style={{ flexShrink: 0 }} /> {apiError}
                  </div>
                )}
                <div className="field field-full">
                  <label htmlFor="muhurat-event">What are you planning?</label>
                  <select id="muhurat-event" value={eventType}
                    onChange={(e) => { setEventType(e.target.value); setSearched(false); }}
                    data-testid="select-muhurat-event">
                    <option value="griha-pravesh">Griha Pravesh · Housewarming</option>
                    <option value="vivah">Vivah Sanskar · Wedding</option>
                    <option value="naamkaran">Naamkaran · Naming ceremony</option>
                    <option value="business">Business opening</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="muhurat-city">Location</label>
                  <select id="muhurat-city" value={city}
                    onChange={(e) => { setCity(e.target.value); setSearched(false); }}
                    data-testid="select-muhurat-city">
                    <option value="new-delhi">New Delhi</option>
                    <option value="mumbai">Mumbai</option>
                    <option value="bengaluru">Bengaluru</option>
                    <option value="jaipur">Jaipur</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="muhurat-date">Preferred date</label>
                  <input id="muhurat-date" type="date" value={date}
                    onChange={(e) => { setDate(e.target.value); setSearched(false); }}
                    data-testid="input-muhurat-date" />
                </div>
                <button className="button button-primary form-submit" type="submit" disabled={isSubmitting} data-testid="button-find-muhurat">
                  {isSubmitting ? (
                    <>
                      <Loader2 size={15} className="animate-spin" /> Finding timings...
                    </>
                  ) : (
                    <>
                      Find auspicious timings <ArrowRight size={15} />
                    </>
                  )}
                </button>
                <p className="muhurat-form-note">
                  <CircleHelp size={14} /> Your final muhurat is best confirmed with a qualified panditji for your personal details.
                </p>
              </form>

              <div className={`muhurat-results ${searched ? 'has-results' : ''}`} aria-live="polite" data-testid="muhurat-results">
                {!searched ? (
                  <div className="muhurat-empty">
                    <div className="muhurat-empty-icon"><CalendarDays size={22} /></div>
                    <span className="section-kicker">Your timings will appear here</span>
                    <h3>Make space for a good beginning.</h3>
                    <p>Select your occasion and location to reveal the day's most supportive windows.</p>
                  </div>
                ) : (
                  <>
                    <div className="muhurat-result-head">
                      <div>
                        <span className="section-kicker">Recommended timings</span>
                        <h3>{eventLabel} in {cityLabel}</h3>
                      </div>
                      <span className="muhurat-date">{date}</span>
                    </div>
                    <div className="timing-list">
                      {displayTimings.map((item, idx) => {
                        const isFeatured = item.is_featured || item.isFeatured || idx === 0;
                        const label = item.label || (idx === 0 ? 'Most auspicious' : idx === 1 ? 'Morning window' : 'Evening window');
                        const timeStr = item.time_range || item.timeRange || '06:18 AM – 07:54 AM';
                        return (
                          <article className={`timing-card ${isFeatured ? 'featured' : ''}`} key={idx}>
                            <div className="timing-icon">
                              {isFeatured ? <Star size={17} /> : idx === 1 ? <SunriseIcon /> : <Sparkles size={17} />}
                            </div>
                            <div>
                              <span className="timing-label">{label}</span>
                              <strong>{timeStr}</strong>
                              <p>{item.description}</p>
                            </div>
                            {isFeatured && <Check size={17} className="timing-check" />}
                          </article>
                        );
                      })}
                    </div>
                    <button className="button button-light muhurat-cta" type="button"
                      data-testid="button-consult-pandit" onClick={() => setModal('launch')}>
                      Consult a Panditji <ArrowRight size={15} />
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* ── Guidance ── */}
        <section className="section section-tint muhurat-guidance" aria-labelledby="guidance-heading" data-testid="section-muhurat-guidance">
          <div className="container-wide guidance-grid">
            <div>
              <span className="section-kicker">A little more context</span>
              <h2 id="guidance-heading">Auspicious does not have to mean complicated.</h2>
            </div>
            <div className="guidance-points">
              <div><span>01</span><p><strong>Choose your intention.</strong> Muhurat is traditionally selected around the nature of the occasion.</p></div>
              <div><span>02</span><p><strong>Make room for your place.</strong> Sunrise, sunset and local panchang timings differ by city.</p></div>
              <div><span>03</span><p><strong>Keep the feeling close.</strong> The best timing is one that helps you begin with clarity and devotion.</p></div>
            </div>
          </div>
        </section>

        {/* ── FAQ ── */}
        <section className="section" aria-labelledby="muhurat-faq-heading" data-testid="section-muhurat-faq">
          <div className="container-wide">
            <div className="section-heading">
              <span className="section-kicker">Common questions</span>
              <h2 id="muhurat-faq-heading">About Muhurat</h2>
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
