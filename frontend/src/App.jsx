import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { SkipLink, Header, PhaseBanner, Footer } from './components';
import DesignSystemPage from './pages/DesignSystemPage';

function PlaceholderHome() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">Civisterial</h1>
      <p>
        Task 1 scaffold is running. Review all design system components on the{' '}
        <Link to="/design" className="text-gov-link underline">
          /design page
        </Link>
        .
      </p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-white text-gov-text">
        <SkipLink />
        <Header />
        <PhaseBanner />
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 w-full max-w-gov mx-auto px-4 py-8"
        >
          <Routes>
            <Route path="/" element={<PlaceholderHome />} />
            <Route path="/design" element={<DesignSystemPage />} />
            <Route path="*" element={<Navigate to="/design" replace />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
