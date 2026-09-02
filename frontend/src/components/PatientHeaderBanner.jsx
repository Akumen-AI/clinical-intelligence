import React from 'react';
import { User } from 'lucide-react';

export default function PatientHeaderBanner({ patient, allergies = [] }) {
  if (!patient) return null;

  return (
    <div className="bg-surface-container-high rounded-2xl border border-outline-variant/30 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
      <div className="flex items-start gap-4">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shrink-0 shadow-inner">
          <User size={28} className="text-on-primary" />
        </div>
        <div>
          <h1 className="text-headline-md font-headline-md text-on-surface leading-tight mb-1">
            {patient.name || 'Unknown Patient'}
          </h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm font-medium text-on-surface-variant">
            <div className="flex items-center gap-1.5">
              <span className="opacity-70">MRN:</span>
              <span className="text-on-surface">{patient.mrn || patient.patient_id}</span>
            </div>
            {patient.dob && (
              <>
                <div className="w-1 h-1 rounded-full bg-outline-variant"></div>
                <div className="flex items-center gap-1.5">
                  <span className="opacity-70">DOB:</span>
                  <span className="text-on-surface">{patient.dob}</span>
                </div>
              </>
            )}
            {patient.sex && (
              <>
                <div className="w-1 h-1 rounded-full bg-outline-variant"></div>
                <div className="flex items-center gap-1.5">
                  <span className="opacity-70">Sex:</span>
                  <span className="text-on-surface capitalize">{patient.sex}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Allergies / Badges */}
      <div className="flex flex-col items-start md:items-end gap-2">
        <div className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/70">Allergies</div>
        <div className="flex flex-wrap gap-2 justify-end">
          {allergies.length > 0 ? allergies.map((allergy, i) => {
            const isSevere = allergy.severity?.toLowerCase() === 'severe';
            const badgeStyle = isSevere 
              ? "bg-error-container/20 text-error border-error/30" 
              : "bg-surface-variant text-on-surface-variant border-outline-variant/30";
              
            return (
              <span 
                key={i} 
                className={`px-3 py-1 border rounded-full text-xs font-bold ${badgeStyle}`}
                title={allergy.reaction ? `Reaction: ${allergy.reaction}` : undefined}
              >
                {allergy.allergen}
              </span>
            );
          }) : (
            <span className="px-3 py-1 bg-surface-variant text-on-surface-variant border border-outline-variant/30 rounded-full text-xs font-semibold">
              No Known Allergies
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
