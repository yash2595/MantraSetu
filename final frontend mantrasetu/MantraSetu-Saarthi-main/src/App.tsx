import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/home';
import KundaliCreation from './pages/kundali';
import MuhuratFinder from './pages/muhurat-finder';
import Login from './pages/login';
import SignUp from './pages/sign-up';
import Puja from './pages/puja';
import NotFound from './pages/not-found';
import Dashboard from './pages/dashboard';
import { ProtectedRoute } from './components/ProtectedRoute';
import { SaarthiProvider } from '@/components/saarthi';

const queryClient = new QueryClient();

function Router() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/puja" element={<Puja />} />
      <Route path="/kundali-creation" element={<KundaliCreation />} />
      <Route path="/muhurat-finder" element={<MuhuratFinder />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/sign-up" element={<SignUp />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <SaarthiProvider>
          <Router />
          <Toaster />
        </SaarthiProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}