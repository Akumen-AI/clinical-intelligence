import React from 'react';
import { User } from 'lucide-react';

export default function PatientHeaderBanner({ patient, allergies = [] }) {
  if (!patient) return null;

  return (
    <div className="bg-surface rounded-2xl border border-line p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
      <div className="flex items-start gap-4">
        <div className="w-14 h-14 rounded-full bg-teal/10 flex items-center justify-center shrink-0">
          <User size={28} className="text-teal" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-ink leading-tight mb-1">
            {patient.name || 'Unknown Patient'}
          </h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm font-medium text-slate">
            <div className="flex items-center gap-1.5">
              <span>MRN:</span>
              <span className="font-mono text-slate">{patient.mrn || patient.patient_id}</span>
            </div>
            {patient.dob && (
              <>
                <div className="w-1 h-1 rounded-full bg-line"></div>
                <div className="flex items-center gap-1.5">
                  <span>DOB:</span>
                  <span className="font-mono text-slate">{patient.dob}</span>
                </div>
              </>
            )}
            {patient.sex && (
              <>
                <div className="w-1 h-1 rounded-full bg-line"></div>
                <div className="flex items-center gap-1.5">
                  <span>Sex:</span>
                  <span className="capitalize text-slate">{patient.sex}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Allergies / Badges */}
      <div className="flex flex-col items-start md:items-end gap-2">
        <div className="text-xs font-bold uppercase tracking-wider text-slate">Allergies</div>
        <div className="flex flex-wrap gap-2 justify-end">
          {allergies.length > 0 ? allergies.map((allergy, i) => {
            const isSevere = allergy.severity?.toLowerCase() === 'severe';
            const badgeStyle = isSevere 
              ? "bg-danger/10 text-danger border-danger/20" 
              : "bg-paper text-slate border-line";
              
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
            <span className="px-3 py-1 bg-paper text-slate border border-line rounded-full text-xs font-semibold">
              No Known Allergies
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
