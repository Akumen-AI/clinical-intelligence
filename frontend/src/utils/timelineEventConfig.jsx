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
      color: 'text-success',
      bg: 'bg-success',
      border: 'border-success/30',
      containerBg: 'bg-success/10',
      icon: <Pill size={16} />,
      label: 'Medication'
    };
  }
  
  if (type.includes('lab') || type.includes('test')) {
    return {
      color: 'text-slate',
      bg: 'bg-teal',
      border: 'border-slate/30',
      containerBg: 'bg-teal/10',
      icon: <Microscope size={16} />,
      label: 'Lab Result'
    };
  }
  
  if (type.includes('diagnos') || type.includes('condition')) {
    return {
      color: 'text-warning',
      bg: 'bg-warning',
      border: 'border-warning/30',
      containerBg: 'bg-warning/10',
      icon: <Activity size={16} />,
      label: 'Diagnosis'
    };
  }
  
  if (type.includes('vital')) {
    return {
      color: 'text-teal',
      bg: 'bg-teal',
      border: 'border-teal/30',
      containerBg: 'bg-teal/10',
      icon: <Activity size={16} />,
      label: 'Vitals'
    };
  }
  
  if (type.includes('procedure') || type.includes('surgery')) {
    return {
      color: 'text-danger',
      bg: 'bg-danger',
      border: 'border-danger/30',
      containerBg: 'bg-danger/10',
      icon: <Syringe size={16} />,
      label: 'Procedure'
    };
  }
  
  if (type.includes('visit') || type.includes('consult')) {
    return {
      color: 'text-slate',
      bg: 'bg-slate',
      border: 'border-slate/30',
      containerBg: 'bg-slate/10',
      icon: <Stethoscope size={16} />,
      label: 'Clinical Visit'
    };
  }

  return {
    color: 'text-teal',
    bg: 'bg-teal',
    border: 'border-teal/30',
    containerBg: 'bg-teal/10',
    icon: <FileText size={16} />,
    label: eventType || 'Clinical Document'
  };
};
