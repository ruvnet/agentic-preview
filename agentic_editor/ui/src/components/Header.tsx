import React from 'react';
import { Link } from 'react-router-dom';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

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
import React from 'react';
import { Link } from 'react-router-dom';

const Header: React.FC = () => {
  return (
    <header className="bg-blue-600 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-2xl font-bold">Agentic Editor</Link>
        <nav>
          <ul className="flex space-x-4">
            <li><Link to="/" className="hover:text-blue-200">Projects</Link></li>
          </ul>
          <DropdownMenu.Root>
            <DropdownMenu.Trigger className="menu-trigger">Options</DropdownMenu.Trigger>
            <DropdownMenu.Content className="dropdown-content">
              <DropdownMenu.Item className="dropdown-item">Profile</DropdownMenu.Item>
              <DropdownMenu.Item className="dropdown-item">Settings</DropdownMenu.Item>
              <DropdownMenu.Separator className="dropdown-separator" />
              <DropdownMenu.Item className="dropdown-item">Logout</DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Root>
        </nav>
      </div>
    </header>
  );
};

export default Header;
