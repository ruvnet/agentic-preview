import React from 'react';
import { Link } from 'react-router-dom';

const Header: React.FC = () => {
  return (
    <header className="bg-white shadow">
      <nav className="container mx-auto px-4 py-4">
        <Link to="/" className="text-xl font-bold text-gray-800">Agentic Editor</Link>
      </nav>
    </header>
  );
};

export default Header;
