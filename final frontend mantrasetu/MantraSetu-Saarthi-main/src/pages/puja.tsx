import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Filter,
  Flame,
  HeartHandshake,
  Loader2,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Star,
  X,
} from 'lucide-react';
import { SiteHeader, SiteFooter, Modal, type ModalType } from '@/components/shared';
import { useSearchParams } from 'react-router-dom';
import { pujaService } from '@/services/puja.service';

interface PujaItem {
  id: string;
  title: string;
  category: 'Home & Family' | 'Dosha & Planetary' | 'Wealth & Success' | 'Health & Protection';
  duration: string;
  price: number;
  rating: number;
  reviewsCount: number;
  image: string;
  description: string;
  popular?: boolean;
}

const defaultPujaCatalog: PujaItem[] = [
  {
    id: 'griha-pravesh',
    title: 'Griha Pravesh Puja & Havan',
    category: 'Home & Family',
    duration: '3.5 Hours',
    price: 5100,
    rating: 4.9,
    reviewsCount: 142,
    image: '/journey-puja.jpg',
    description: 'Traditional housewarming ceremony to purify the home, invite divine peace, and invoke Lord Ganesha and Vastu Purush blessings.',
    popular: true,
  },
  {
    id: 'satyanarayan',
    title: 'Satyanarayan Katha & Puja',
    category: 'Home & Family',
    duration: '2.5 Hours',
    price: 3500,
    rating: 4.8,
    reviewsCount: 98,
    image: '/journey-explore.jpg',
    description: 'Auspicious ritual dedicated to Lord Vishnu for family well-being, harmony, gratitude, and fulfillment of earnest desires.',
    popular: true,
  },
  {
    id: 'navgraha-shanti',
    title: 'Navgraha Shanti Puja',
    category: 'Dosha & Planetary',
    duration: '3 Hours',
    price: 4800,
    rating: 4.9,
    reviewsCount: 116,
    image: '/journey-muhurat.jpg',
    description: 'Pacifies planetary doshas and balances the cosmic influences of all nine planets in your birth chart for stability and health.',
  },
  {
    id: 'mahaprashad-mrityunjaya',
    title: 'Maha Mrityunjaya Havan',
    category: 'Health & Protection',
    duration: '4 Hours',
    price: 7500,
    rating: 5.0,
    reviewsCount: 84,
    image: '/special-pujas.jpg',
    description: 'Powerful Shiva fire ritual invoking supreme protection, longevity, physical healing, and peace from negative energies.',
    popular: true,
  },
  {
    id: 'laxmi-kuber',
    title: 'Laxmi Kuber Wealth Puja',
    category: 'Wealth & Success',
    duration: '2 Hours',
    price: 4100,
    rating: 4.8,
    reviewsCount: 76,
    image: '/temple-hero.jpg',
    description: 'Invokes Goddess Laxmi and Lord Kuber for financial growth, business prosperity, clearance of debts, and material success.',
  },
  {
    id: 'rudrabhishek',
    title: 'Rudra Abhishek Puja',
    category: 'Health & Protection',
    duration: '2.5 Hours',
    price: 4500,
    rating: 4.9,
    reviewsCount: 130,
    image: '/journey-pandit.jpg',
    description: 'Sacred Vedic bathing of Shiva Lingam with 108 mantras, milk, honey and holy water for removing life obstacles.',
  },
  {
    id: 'kalsarp-dosha',
    title: 'Kalsarp Dosha Nivaran Puja',
    category: 'Dosha & Planetary',
    duration: '4 Hours',
    price: 6500,
    rating: 4.9,
    reviewsCount: 62,
    image: '/journey-muhurat.jpg',
    description: 'Specialised Vedic ritual performed to alleviate Kalsarp dosha and Rahu-Ketu impediments in career and personal life.',
  },
  {
    id: 'ganesh-puja',
    title: 'Ganesh Puja & Havan',
    category: 'Wealth & Success',
    duration: '2 Hours',
    price: 3100,
    rating: 4.9,
    reviewsCount: 154,
    image: '/journey-puja.jpg',
    description: 'First ceremony performed before new business launches, shop openings, or major life ventures to remove all obstacles.',
  },
];

const categories = ['All Pujas', 'Home & Family', 'Dosha & Planetary', 'Wealth & Success', 'Health & Protection'] as const;

export default function Puja() {
  const [modal, setModal] = useState<ModalType>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('All Pujas');
  const [searchParams] = useSearchParams();
  const initialSearch = searchParams.get('q') || '';
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [bookingPuja, setBookingPuja] = useState<PujaItem | null>(null);
  const [pujas, setPujas] = useState<PujaItem[]>(defaultPujaCatalog);

  useEffect(() => {
    if (searchParams.get('q')) {
      setSearchQuery(searchParams.get('q') || '');
    }
  }, [searchParams]);

  // Auto-open booking modal if autobook=true in URL parameter and matched pujas exist
  useEffect(() => {
    const isAutoBook = searchParams.get('autobook') === 'true';
    if (isAutoBook && filteredPujas.length > 0 && !bookingPuja) {
      const timer = setTimeout(() => {
        console.log('[PUJA-PAGE] Autobook parameter active: Opening booking modal for:', filteredPujas[0].title);
        setBookingPuja(filteredPujas[0]);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [searchParams, filteredPujas, bookingPuja]);


  // Form state for booking modal
  const [bookingDate, setBookingDate] = useState('2026-08-15');
  const [bookingCity, setBookingCity] = useState('New Delhi');
  const [bookingTime, setBookingTime] = useState('09:00 AM');
  const [devoteeName, setDevoteeName] = useState('');
  const [devoteePhone, setDevoteePhone] = useState('');
  const [bookingSubmitted, setBookingSubmitted] = useState(false);
  const [isBookingSubmitting, setIsBookingSubmitting] = useState(false);
  const [bookingError, setBookingError] = useState<string | null>(null);

  // Fetch Live Puja Catalog from GET /puja/list
  useEffect(() => {
    let isMounted = true;
    const fetchCatalog = async () => {
      try {
        const data = await pujaService.listPujas();
        if (isMounted && data && Array.isArray(data) && data.length > 0) {
          const mapped: PujaItem[] = data.map((item, idx) => ({
            id: item.id || `puja-${idx}`,
            title: item.title,
            category: (['Home & Family', 'Dosha & Planetary', 'Wealth & Success', 'Health & Protection'].includes(item.category)
              ? item.category
              : 'Home & Family') as PujaItem['category'],
            duration: item.duration || '3 Hours',
            price: item.price || 3500,
            rating: item.rating || 4.9,
            reviewsCount: item.reviewsCount || item.reviews_count || 100,
            image: item.image || defaultPujaCatalog[idx % defaultPujaCatalog.length].image,
            description: item.description,
            popular: item.popular ?? idx < 3,
          }));
          setPujas(mapped);
        }
      } catch {
        // Fall back to default catalog if backend API is offline or returns error
      }
    };

    fetchCatalog();
    return () => {
      isMounted = false;
    };
  }, []);

  const filteredPujas = useMemo(() => {
    return pujas.filter((puja) => {
      const matchesCategory = selectedCategory === 'All Pujas' || puja.category === selectedCategory;
      const matchesSearch =
        puja.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        puja.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [pujas, selectedCategory, searchQuery]);

  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bookingPuja) return;

    setIsBookingSubmitting(true);
    setBookingError(null);

    try {
      await pujaService.bookPuja({
        puja_id: bookingPuja.id,
        puja_title: bookingPuja.title,
        city: bookingCity,
        date: bookingDate,
        time: bookingTime,
        devotee_name: devoteeName,
        phone: devoteePhone,
      });
      setBookingSubmitted(true);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unable to confirm booking. Please try again.';
      setBookingError(errorMessage);
    } finally {
      setIsBookingSubmitting(false);
    }
  };

  const closeBookingModal = () => {
    setBookingPuja(null);
    setBookingSubmitted(false);
  };

  return (
    <div className="page-shell">
      <SiteHeader onOpenModal={setModal} />

      <main>
        {/* ── Hero ── */}
        <section className="tool-hero" aria-labelledby="puja-page-title" data-testid="section-puja-hero">
          <div className="container-wide tool-hero-inner">
            <div className="tool-hero-copy">
              <span className="eyebrow">Sacred ceremonies for every milestone</span>
              <h1 id="puja-page-title">
                Book Authentic Pujas<br />
                <em>with Verified Panditjis.</em>
              </h1>
              <p>
                Choose from traditional Vedic ceremonies conducted with devotion, complete authentic samagri, and verified priests at your home or venue.
              </p>
              <div className="hero-trust" aria-label="Puja service trust signals">
                <span><ShieldCheck size={15} /> Verified Vedic Panditjis</span>
                <span><Flame size={15} /> Authentic Samagri Included</span>
                <span><HeartHandshake size={15} /> Punctual & Dedicated</span>
              </div>
            </div>
            <div className="tool-hero-mark" aria-hidden="true">
              <div className="tool-orbit tool-orbit-one" />
              <div className="tool-orbit tool-orbit-two" />
              <Flame size={52} strokeWidth={1.1} />
            </div>
          </div>
        </section>

        {/* ── Filter & Search Section ── */}
        <section id="puja-catalog-section" className="section" aria-labelledby="catalog-heading" data-testid="section-puja-catalog">
          <div className="container-wide">
            <div className="section-heading centered">
              <span className="section-kicker">Sacred Ceremonies</span>
              <h2 id="catalog-heading">Explore Our Puja Services</h2>
              <p>Select an occasion or filter by category to find the sacred ritual for your home, family, or business.</p>
            </div>

            {/* Search and Category Bar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', marginBottom: '2.5rem' }}>
              <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center', background: '#fffdf9', padding: '0.6rem 1rem', border: '1px solid #eadbc9', borderRadius: '0.5rem', boxShadow: 'var(--shadow-sm)' }}>
                <Search size={18} color="#d96620" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by puja name, deity, or occasion..."
                  style={{ border: 0, outline: 0, width: '100%', background: 'transparent', fontSize: '0.88rem', color: '#292a2e' }}
                  data-testid="input-search-puja"
                />
                {searchQuery && (
                  <button type="button" onClick={() => setSearchQuery('')} style={{ border: 0, background: 'transparent', cursor: 'pointer', color: '#887765' }}>
                    <X size={16} />
                  </button>
                )}
              </div>

              {/* Category Pills */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.55rem', alignItems: 'center' }} role="tablist" aria-label="Puja categories">
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#887765', textTransform: 'uppercase', letterSpacing: '0.08em', marginRight: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <Filter size={13} /> Filter:
                </span>
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    role="tab"
                    aria-selected={selectedCategory === cat}
                    onClick={() => setSelectedCategory(cat)}
                    style={{
                      padding: '0.45rem 0.85rem',
                      borderRadius: '999px',
                      border: '1px solid',
                      borderColor: selectedCategory === cat ? '#ee7c2b' : '#eadbc9',
                      background: selectedCategory === cat ? '#ee7c2b' : '#fffdf9',
                      color: selectedCategory === cat ? '#ffffff' : '#5c5248',
                      fontSize: '0.74rem',
                      fontWeight: 800,
                      cursor: 'pointer',
                      transition: 'all 160ms ease',
                    }}
                    data-testid={`tab-category-${cat.toLowerCase().replaceAll(' ', '-')}`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Puja Cards Grid */}
            {filteredPujas.length === 0 ? (
              <div className="muhurat-empty" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
                <Sparkles size={32} color="#d96620" style={{ margin: '0 auto 1rem' }} />
                <h3>No matching pujas found</h3>
                <p>Try searching for "Griha Pravesh", "Vishnu", or "Havan".</p>
              </div>
            ) : (
              <div className="service-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>
                {filteredPujas.map((puja) => (
                  <article className="service-card" key={puja.id} style={{ padding: '0', overflow: 'hidden', height: '100%', display: 'flex', flexDirection: 'column' }} data-testid={`card-puja-${puja.id}`}>
                    <div style={{ position: 'relative', height: '160px', overflow: 'hidden', background: '#4a2616' }}>
                      <img
                        src={puja.image}
                        alt={puja.title}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', transition: 'transform 400ms ease' }}
                      />
                      <span style={{ position: 'absolute', top: '0.65rem', left: '0.65rem', padding: '0.25rem 0.55rem', borderRadius: '0.35rem', background: 'rgba(36, 18, 10, 0.78)', color: '#ffc477', fontSize: '0.64rem', fontWeight: 800, backdropFilter: 'blur(4px)' }}>
                        {puja.category}
                      </span>
                      {puja.popular && (
                        <span style={{ position: 'absolute', top: '0.65rem', right: '0.65rem', padding: '0.25rem 0.55rem', borderRadius: '0.35rem', background: '#ee7c2b', color: '#fff', fontSize: '0.64rem', fontWeight: 800 }}>
                          Popular
                        </span>
                      )}
                    </div>

                    <div style={{ padding: '1.2rem', display: 'flex', flexDirection: 'column', flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#d96620', fontSize: '0.74rem', fontWeight: 800 }}>
                          <Star size={13} fill="currentColor" />
                          <span>{puja.rating}</span>
                          <span style={{ color: '#887765', fontWeight: 500 }}>({puja.reviewsCount})</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#776e65', fontSize: '0.72rem' }}>
                          <Clock size={12} />
                          <span>{puja.duration}</span>
                        </div>
                      </div>

                      <h3 style={{ margin: '0.2rem 0 0.45rem', fontSize: '1.05rem', color: '#24272d', fontWeight: 800 }}>
                        {puja.title}
                      </h3>
                      <p style={{ margin: 0, fontSize: '0.78rem', color: '#68645f', lineHeight: 1.5, flex: 1 }}>
                        {puja.description}
                      </p>

                      <div style={{ marginTop: '1.1rem', paddingTop: '0.8rem', borderTop: '1px solid #f2e4d3', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <span style={{ display: 'block', fontSize: '0.64rem', color: '#887765', textTransform: 'uppercase', fontWeight: 800 }}>Starting from</span>
                          <strong style={{ fontSize: '1.1rem', color: '#24272d' }}>₹{puja.price.toLocaleString('en-IN')}</strong>
                        </div>
                        <button
                          className="button button-primary"
                          type="button"
                          onClick={() => setBookingPuja(puja)}
                          style={{ minHeight: '36px', padding: '0.45rem 0.9rem', fontSize: '0.74rem' }}
                          data-testid={`button-book-now-${puja.id}`}
                        >
                          Book Now <ArrowRight size={13} />
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ── Booking Modal Placeholder ── */}
        {bookingPuja && (
          <div className="modal-backdrop open" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) closeBookingModal(); }}>
            <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="booking-title" style={{ maxWidth: 540 }}>
              <button className="modal-close" type="button" onClick={closeBookingModal} aria-label="Close dialog">
                <X size={16} />
              </button>

              {bookingSubmitted ? (
                <div style={{ textAlign: 'center', padding: '1rem 0' }} data-testid="status-booking-success">
                  <div style={{ width: 52, height: 52, borderRadius: '50%', background: '#e9f4e7', color: '#27ae60', display: 'grid', placeItems: 'center', margin: '0 auto 1rem' }}>
                    <CheckCircle2 size={28} />
                  </div>
                  <span className="section-kicker">Booking Received</span>
                  <h2 id="booking-title" style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Your Puja Reservation is Confirmed!</h2>
                  <p style={{ color: '#68645f', fontSize: '0.84rem', lineHeight: 1.6, maxWidth: 420, margin: '0 auto 1.4rem' }}>
                    Thank you, <strong>{devoteeName || 'Devotee'}</strong>. Our verified panditji will call you to confirm location details for <strong>{bookingPuja.title}</strong> on <strong>{bookingDate}</strong>.
                  </p>
                  <div style={{ padding: '0.8rem', background: '#fff0d9', borderRadius: '0.45rem', fontSize: '0.75rem', color: '#7a3e1e', marginBottom: '1.4rem' }}>
                    * Demo mode: No payment has been processed. Complete samagri list will be sent via SMS/WhatsApp.
                  </div>
                  <button className="button button-primary" type="button" onClick={closeBookingModal}>
                    Done
                  </button>
                </div>
              ) : (
                <>
                  <span className="section-kicker">Reservation Details</span>
                  <h2 id="booking-title" style={{ fontSize: '1.45rem', marginBottom: '0.2rem' }}>Book {bookingPuja.title}</h2>
                  <p style={{ fontSize: '0.8rem', color: '#776e65', marginBottom: '1.1rem' }}>
                    Duration: <strong>{bookingPuja.duration}</strong> · Price: <strong>₹{bookingPuja.price.toLocaleString('en-IN')}</strong> (Samagri included)
                  </p>

                  <form className="modal-form" onSubmit={handleBookingSubmit} data-testid="form-puja-booking">
                    {bookingError && (
                      <div className="field-error" role="alert" style={{ padding: '0.65rem 0.85rem', background: '#fdf2f2', border: '1px solid #f8b4b4', borderRadius: '0.45rem', color: '#9b1c1c', fontSize: '0.78rem', marginBottom: '0.5rem' }}>
                        <ShieldAlert size={16} style={{ flexShrink: 0 }} /> {bookingError}
                      </div>
                    )}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                      <div className="field">
                        <label htmlFor="booking-city">City</label>
                        <select id="booking-city" value={bookingCity} onChange={(e) => setBookingCity(e.target.value)} required>
                          <option value="New Delhi">New Delhi</option>
                          <option value="Mumbai">Mumbai</option>
                          <option value="Bengaluru">Bengaluru</option>
                          <option value="Jaipur">Jaipur</option>
                          <option value="Varanasi">Varanasi</option>
                        </select>
                      </div>
                      <div className="field">
                        <label htmlFor="booking-date">Ceremony Date</label>
                        <input id="booking-date" type="date" value={bookingDate} onChange={(e) => setBookingDate(e.target.value)} required />
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                      <div className="field">
                        <label htmlFor="booking-time">Time Slot</label>
                        <select id="booking-time" value={bookingTime} onChange={(e) => setBookingTime(e.target.value)}>
                          <option value="06:00 AM">06:00 AM (Brahma Muhurat)</option>
                          <option value="09:00 AM">09:00 AM (Morning)</option>
                          <option value="04:00 PM">04:00 PM (Evening)</option>
                        </select>
                      </div>
                      <div className="field">
                        <label htmlFor="devotee-name">Your Full Name</label>
                        <input id="devotee-name" required placeholder="Enter your name" value={devoteeName} onChange={(e) => setDevoteeName(e.target.value)} />
                      </div>
                    </div>

                    <div className="field">
                      <label htmlFor="devotee-phone">Mobile Number (for Panditji confirmation)</label>
                      <input id="devotee-phone" type="tel" required placeholder="+91 XXXXX XXXXX" value={devoteePhone} onChange={(e) => setDevoteePhone(e.target.value)} />
                    </div>

                    <button className="button button-primary" type="submit" disabled={isBookingSubmitting} style={{ width: '100%', marginTop: '0.4rem' }} data-testid="button-confirm-booking">
                      {isBookingSubmitting ? (
                        <>
                          <Loader2 size={15} className="animate-spin" /> Confirming Reservation...
                        </>
                      ) : (
                        <>
                          Confirm Reservation <ArrowRight size={15} />
                        </>
                      )}
                    </button>
                  </form>
                </>
              )}
            </div>
          </div>
        )}
      </main>

      <SiteFooter />
      <Modal modal={modal} onClose={() => setModal(null)} />
    </div>
  );
}
