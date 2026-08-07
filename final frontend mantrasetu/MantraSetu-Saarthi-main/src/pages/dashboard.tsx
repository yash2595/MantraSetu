import { SiteHeader, SiteFooter } from '@/components/shared';
import { useAuth } from '@/contexts/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();
  
  return (
    <div className="page-shell">
      <SiteHeader />
      <main style={{ padding: '4rem 2rem', maxWidth: '1200px', margin: '0 auto', flex: 1 }}>
        <h1 style={{ fontSize: '2rem', color: '#3d2b1f', marginBottom: '1rem' }}>Welcome to your Dashboard</h1>
        <div style={{ background: '#fff', padding: '2rem', borderRadius: '12px', border: '1px solid #efe8e1' }}>
          <p style={{ fontSize: '1.1rem', color: '#68645f' }}>
            Hello, <strong>{user?.name || 'Devotee'}</strong>!
          </p>
          <p style={{ marginTop: '1rem', color: '#8a7d70' }}>
            This is your private space. You can view your booked pujas, saved kundalis, and account settings here.
          </p>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
