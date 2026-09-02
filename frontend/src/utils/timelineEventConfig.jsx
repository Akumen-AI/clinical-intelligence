import React from 'react';
import {
  FileText,
  Activity,
  Syringe,
  Pill,
  Stethoscope,
  Microscope,
} from 'lucide-react';

export const getEventConfig = (eventType) => {
  const type = (eventType || '').toLowerCase();
  
  if (type.includes('medication') || type.includes('med-change') || type.includes('prescription')) {
    return {
      color: 'text-emerald-500',
      bg: 'bg-emerald-500',
      border: 'border-emerald-500/30',
      containerBg: 'bg-emerald-500/10',
      icon: <Pill size={16} />,
      label: 'Medication'
    };
  }
  
  if (type.includes('lab') || type.includes('test')) {
    return {
      color: 'text-violet-500',
      bg: 'bg-violet-500',
      border: 'border-violet-500/30',
      containerBg: 'bg-violet-500/10',
      icon: <Microscope size={16} />,
      label: 'Lab Result'
    };
  }
  
  if (type.includes('diagnos') || type.includes('condition')) {
    return {
      color: 'text-amber-500',
      bg: 'bg-amber-500',
      border: 'border-amber-500/30',
      containerBg: 'bg-amber-500/10',
      icon: <Activity size={16} />,
      label: 'Diagnosis'
    };
  }
  
  if (type.includes('vital')) {
    return {
      color: 'text-cyan-500',
      bg: 'bg-cyan-500',
      border: 'border-cyan-500/30',
      containerBg: 'bg-cyan-500/10',
      icon: <Activity size={16} />,
      label: 'Vitals'
    };
  }
  
  if (type.includes('procedure') || type.includes('surgery')) {
    return {
      color: 'text-rose-500',
      bg: 'bg-rose-500',
      border: 'border-rose-500/30',
      containerBg: 'bg-rose-500/10',
      icon: <Syringe size={16} />,
      label: 'Procedure'
    };
  }
  
  if (type.includes('visit') || type.includes('consult')) {
    return {
      color: 'text-indigo-500',
      bg: 'bg-indigo-500',
      border: 'border-indigo-500/30',
      containerBg: 'bg-indigo-500/10',
      icon: <Stethoscope size={16} />,
      label: 'Clinical Visit'
    };
  }

  return {
    color: 'text-primary',
    bg: 'bg-primary',
    border: 'border-primary/30',
    containerBg: 'bg-primary/10',
    icon: <FileText size={16} />,
    label: eventType || 'Clinical Document'
  };
};
