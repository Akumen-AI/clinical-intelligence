import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

export default function ConfirmDialog({ 
  isOpen, 
  title, 
  message, 
  confirmText = "Confirm", 
  cancelText = "Cancel", 
  onConfirm, 
  onCancel, 
  isDanger = false 
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-surface-container border border-outline-variant/30 rounded-2xl shadow-2xl max-w-md w-full animate-in zoom-in-95 duration-200"
        role="dialog"
      >
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <div className={`p-3 rounded-full ${isDanger ? 'bg-error-container/20 text-error' : 'bg-primary/20 text-primary'}`}>
              <AlertTriangle size={24} />
            </div>
            <button 
              onClick={onCancel}
              className="text-on-surface-variant hover:text-on-surface hover:bg-surface-variant p-2 rounded-lg transition-colors"
            >
              <X size={20} />
            </button>
          </div>
          
          <h2 className="text-xl font-headline-md text-on-surface mb-2">{title}</h2>
          <p className="text-body-md text-on-surface-variant mb-8">{message}</p>
          
          <div className="flex justify-end gap-3">
            <button 
              onClick={onCancel}
              className="px-5 py-2.5 rounded-lg font-semibold text-sm bg-surface-variant border border-outline-variant/30 text-on-surface hover:bg-surface-variant/80 transition-colors"
            >
              {cancelText}
            </button>
            <button 
              onClick={onConfirm}
              className={`px-5 py-2.5 rounded-lg font-semibold text-sm shadow-lg transition-all ${
                isDanger 
                  ? 'bg-error text-on-error hover:bg-error/90 shadow-error/20' 
                  : 'bg-primary text-on-primary hover:bg-primary/90 shadow-primary/20'
              }`}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
