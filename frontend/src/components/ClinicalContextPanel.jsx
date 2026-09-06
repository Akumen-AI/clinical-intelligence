/**
 * Story 10.1 / FR-32 — ClinicalContextPanel
 *
 * Displays medications, allergies, prior lab results, and history
 * from the canonical record. Rendered automatically when the
 * patient profile (note-entry screen) opens.
 *
 * AC-3: This component has NO knowledge of diagnoses, ICD codes,
 * condition labels, or any language that could constitute a
 * clinical suggestion. Any such data silently passed in props
 * is ignored at render time (see render guards below).
 */
import React from 'react';
import { Pill, FlaskConical, ShieldAlert, ClipboardList, Info } from 'lucide-react';

const Section = ({ icon: Icon, title, color, children, emptyText }) => (
  <div className="mb-4">
    <div
      className="flex items-center gap-2 mb-2 pb-1 border-b border-outline-variant/20"
    >
      <Icon size={14} className={color} />
      <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
        {title}
      </span>
    </div>
    {React.Children.count(children) === 0 ? (
      <p className="text-xs text-on-surface-variant/60 italic">{emptyText}</p>
    ) : (
      children
    )}
  </div>
);

export default function ClinicalContextPanel({ panel, loading, error }) {
  /* ── AC-3 runtime guard: drop any accidentally injected diag keys ── */
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
      <div className="bg-surface-container rounded-2xl border border-outline-variant/30 p-4 shadow-sm flex items-center justify-center min-h-[200px]">
        <p className="text-xs text-on-surface-variant animate-pulse">Loading context…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-error-container/10 rounded-2xl border border-error/20 p-4 text-xs text-error flex items-center gap-2">
        <ShieldAlert size={14} />
        <span>Could not load context panel.</span>
      </div>
    );
  }

  return (
    <aside
      className="bg-surface-container rounded-2xl border border-outline-variant/30 p-4 shadow-sm flex flex-col gap-1"
      aria-label="Clinical context panel"
      data-testid="clinical-context-panel"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <ClipboardList size={16} className="text-primary" />
        <h3 className="text-sm font-bold text-on-surface">Existing Patient Context</h3>
        <span className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-[10px] font-bold text-primary uppercase tracking-wide">
          <Info size={10} /> Record Only
        </span>
      </div>

      {/* Medications */}
      <Section
        icon={Pill}
        title="Medications"
        color="text-emerald-500"
        emptyText="No medications on record."
      >
        {safeMedications.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {safeMedications.map((m) => (
              <li
                key={m.id}
                className="bg-surface-container-high rounded-lg px-3 py-2 text-xs"
              >
                <span className="text-on-surface font-medium">{m.raw_text}</span>
                {m.rxnorm_code && (
                  <span className="ml-2 text-on-surface-variant">
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
        color="text-error"
        emptyText="No known allergies on record."
      >
        {allergies.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {allergies.map((a, i) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-error-container/20 text-error border border-error/30 rounded-full text-[11px] font-bold"
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
        color="text-violet-500"
        emptyText="No prior lab results on record."
      >
        {safePriorResults.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {safePriorResults.map((r) => (
              <li
                key={r.id}
                className="bg-surface-container-high rounded-lg px-3 py-2 text-xs"
              >
                <span className="text-on-surface font-medium">{r.raw_text}</span>
                {r.loinc_code && (
                  <span className="ml-2 text-on-surface-variant">
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
        color="text-cyan-500"
        emptyText="No medical history on record."
      >
        {history.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {history.map((h, i) => (
              <li
                key={i}
                className="bg-surface-container-high rounded-lg px-3 py-2 text-xs text-on-surface"
              >
                {h}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* Source badge — AC-2 proof for the operator */}
      <div className="mt-2 pt-2 border-t border-outline-variant/20 flex items-center gap-1 text-[10px] text-on-surface-variant/60">
        <Info size={10} />
        Source: {panel?.source ?? 'canonical_record'}
      </div>
    </aside>
  );
}
