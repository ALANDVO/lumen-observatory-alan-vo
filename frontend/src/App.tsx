import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { ActorsPage } from './pages/ActorsPage';
import { MetricsPage } from './pages/MetricsPage';

const navigation = [
  { path: '/', label: 'Actors' },
  { path: '/metrics', label: 'Metrics' },
];

export default function App() {
  const location = useLocation();

  return (
    <Layout>
      <nav className="mb-6" aria-label="Main navigation">
        <ul className="flex gap-1" role="tablist">
          {navigation.map((item) => (
            <li key={item.path} role="presentation">
              <Link
                to={item.path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === item.path
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
                role="tab"
                aria-selected={location.pathname === item.path}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <Routes>
        <Route path="/" element={<ActorsPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
      </Routes>
    </Layout>
  );
}