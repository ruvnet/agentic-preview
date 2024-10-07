import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';

function SettingsDialog() {
  return (
    <Dialog.Root>
      <Dialog.Trigger className="btn">Open Settings</Dialog.Trigger>
      <Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="dialog-content">
        <Dialog.Title>Settings</Dialog.Title>
        <Dialog.Description>Configure your preferences here.</Dialog.Description>
        {/* Add settings form elements here */}
        <Dialog.Close className="btn">Close</Dialog.Close>
      </Dialog.Content>
    </Dialog.Root>
  );
}

export default SettingsDialog;
