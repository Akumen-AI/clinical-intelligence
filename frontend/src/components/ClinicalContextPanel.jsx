import React from 'react';
import { Pill, FlaskConical, ShieldAlert, ClipboardList, Info } from 'lucide-react';

const Section = ({ icon: Icon, title, color, children, emptyText }) => (
  <div className="mb-4">
    <div
      className="flex items-center gap-2 mb-2 pb-1 border-b border-line"
    >
      <Icon size={14} className={color} />
      <span className="text-xs font-bold uppercase tracking-wider text-slate">
        {title}
      </span>
    </div>
    {React.Children.count(children) === 0 ? (
      <p className="text-xs text-slate italic opacity-80">{emptyText}</p>
    ) : (
      children
    )}
  </div>
);

export default function ClinicalContextPanel({ panel, loading, error }) {
  const safeMedications = (panel?.medications ?? []).map(({ id, raw_text, rxnorm_code }) => ({
    id,
    raw_text,
    rxnorm_code,
  }));

  const safePriorResults = (panel?.prior_results ?? []).map(
    ({ id, raw_text, loinc_code }) => ({ id, raw_text, loinc_code })
  );

  const allergies = panel?.allergies ?? [];
  const history = panel?.history ?? [];

  if (loading) {
    return (
      <div className="bg-surface rounded-2xl border border-line p-4 shadow-sm flex items-center justify-center min-h-[200px]">
        <p className="text-xs text-slate animate-pulse">Loading context…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-danger/10 rounded-2xl border border-danger/20 p-4 text-xs text-danger flex items-center gap-2">
        <ShieldAlert size={14} />
        <span>Could not load context panel.</span>
      </div>
    );
  }

  return (
    <aside
      className="bg-surface rounded-2xl border border-line p-4 shadow-sm flex flex-col gap-1"
      aria-label="Clinical context panel"
      data-testid="clinical-context-panel"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <ClipboardList size={16} className="text-teal" />
        <h3 className="text-sm font-bold text-ink">Existing Patient Context</h3>
        <span className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full bg-teal/10 border border-teal/20 text-[10px] font-bold text-teal uppercase tracking-wide">
          <Info size={10} /> Record Only
        </span>
      </div>

      {/* Medications */}
      <Section
        icon={Pill}
        title="Medications"
        color="text-teal"
        emptyText="No medications on record."
      >
        {safeMedications.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {safeMedications.map((m) => (
              <li
                key={m.id}
                className="bg-paper rounded-lg px-3 py-2 text-xs"
              >
                <span className="text-ink font-medium">{m.raw_text}</span>
                {m.rxnorm_code && (
                  <span className="ml-2 font-mono text-[10px] text-slate bg-surface px-1.5 py-0.5 rounded-md border border-line">
                    RxNorm: {m.rxnorm_code}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* Allergies */}
      <Section
        icon={ShieldAlert}
        title="Allergies"
        color="text-danger"
        emptyText="No known allergies on record."
      >
        {allergies.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {allergies.map((a, i) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-danger/10 text-danger border border-danger/20 rounded-full text-[11px] font-bold"
              >
                {a}
              </span>
            ))}
          </div>
        )}
      </Section>

      {/* Prior Lab Results */}
      <Section
        icon={FlaskConical}
        title="Prior Results"
        color="text-teal"
        emptyText="No prior lab results on record."
      >
        {safePriorResults.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {safePriorResults.map((r) => (
              <li
                key={r.id}
                className="bg-paper rounded-lg px-3 py-2 text-xs"
              >
                <span className="text-ink font-medium">{r.raw_text}</span>
                {r.loinc_code && (
                  <span className="ml-2 font-mono text-[10px] text-slate bg-surface px-1.5 py-0.5 rounded-md border border-line">
                    LOINC: {r.loinc_code}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* History */}
      <Section
        icon={ClipboardList}
        title="History"
        color="text-teal"
        emptyText="No medical history on record."
      >
        {history.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {history.map((h, i) => (
              <li
                key={i}
                className="bg-paper rounded-lg px-3 py-2 text-xs text-ink"
              >
                {h}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* Source badge — AC-2 proof for the operator */}
      <div className="mt-2 pt-2 border-t border-line flex items-center gap-1 text-[10px] text-slate">
        <Info size={10} />
        Source: {panel?.source ?? 'canonical_record'}
      </div>
    </aside>
  );
}
