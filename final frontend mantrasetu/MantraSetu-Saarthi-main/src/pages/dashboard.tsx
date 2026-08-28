import { SiteHeader, SiteFooter } from '@/components/shared';
import { useAuth } from '@/contexts/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();
  
  return (
    <div className="page-shell">
      <SiteHeader />
      <main style={{ padding: '4rem 2rem', maxWidth: '1200px', margin: '0 auto', flex: 1, width: '100%' }}>
        <h1 style={{ fontSize: '2rem', color: '#3d2b1f', marginBottom: '1rem' }}>Welcome to your Dashboard</h1>
        <div style={{ background: '#fff', padding: '2rem', borderRadius: '12px', border: '1px solid #efe8e1', marginBottom: '1.5rem' }}>
          <p style={{ fontSize: '1.1rem', color: '#68645f' }}>
            Hello, <strong>{user?.name || 'User'}</strong>!
          </p>
          <p style={{ marginTop: '1rem', color: '#8a7d70' }}>
            {user?.role === 'pandit' 
              ? 'Welcome to your Pandit portal. Here you can track your application and manage your profile.'
              : 'This is your private space. You can view your booked pujas, saved kundalis, and account settings here.'}
          </p>
        </div>

        {user?.role === 'pandit' && (
          <div style={{ background: '#fffaf2', padding: '1.5rem', borderRadius: '12px', border: '1px solid #d99c6b' }}>
            <h2 style={{ fontSize: '1.25rem', color: '#d96620', margin: '0 0 1rem 0' }}>Verification Status</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <strong style={{ minWidth: '120px' }}>Current Status:</strong>
              <span style={{
                padding: '0.3rem 0.8rem',
                borderRadius: '20px',
                fontSize: '0.85rem',
                fontWeight: 600,
                textTransform: 'capitalize',
                background: user.application_status === 'approved' ? '#dcfce7' : user.application_status === 'rejected' ? '#fee2e2' : '#fef9c3',
                color: user.application_status === 'approved' ? '#166534' : user.application_status === 'rejected' ? '#991b1b' : '#854d0e',
              }}>
                {user.application_status || 'Pending'}
              </span>
            </div>
            <p style={{ color: '#68645f', fontSize: '0.9rem', marginTop: '1rem' }}>
              {user.application_status === 'approved' 
                ? 'Congratulations! Your profile is verified and active.'
                : user.application_status === 'rejected'
                  ? 'Your application was rejected. Please contact support for more details.'
                  : 'Your profile is currently under review by our verification team. You will be notified once it is approved (usually within 24-48 hours).'}
            </p>
          </div>
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
