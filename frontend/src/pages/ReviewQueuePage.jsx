import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ClipboardCheck,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  ChevronDown,
  InboxIcon,
} from 'lucide-react';
import ReviewFieldCard from '../components/ReviewFieldCard';
import {
  fetchPendingReviews,
  fetchReviewContext,
  submitReviewAction,
  getReviewImageUrl,
  getDocumentStaticUrl,
} from '../services/api';

export default function ReviewQueuePage() {
  const [allItems, setAllItems] = useState([]);      // all PENDING review items
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Current document filter
  const [selectedDocId, setSelectedDocId] = useState('ALL');

  // Items for the selected document (or all docs)
  const [docItems, setDocItems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Context for the currently focused item (enriched with doc info + bbox)
  const [context, setContext] = useState(null);
  const [isLoadingContext, setIsLoadingContext] = useState(false);

  // Image display state
  const [imgSrc, setImgSrc] = useState(null);
  const [imgError, setImgError] = useState(false);
  const [showFullPage, setShowFullPage] = useState(false);
  const [zoom, setZoom] = useState(1.0);
  const [imgLoaded, setImgLoaded] = useState(false);

  // Action state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

  // Stats
  const [reviewedToday, setReviewedToday] = useState(0);
  const startTimeRef = useRef(Date.now());

  // ── Load all pending items ──────────────────────────────────────────────
  const loadQueue = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchPendingReviews(null, 1, 100);
      setAllItems(data.items || []);
    } catch (err) {
      // Safely convert error detail to string — it can be an array (Pydantic) or object
      const raw = err.response?.data?.detail;
      let msg;
      if (typeof raw === 'string') msg = raw;
      else if (Array.isArray(raw)) msg = raw.map((e) => e.msg || JSON.stringify(e)).join('; ');
      else if (raw) msg = JSON.stringify(raw);
      else msg = err.message || 'Failed to load review queue';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // ── Recompute docItems when allItems or selectedDocId changes ──────────
  useEffect(() => {
    const filtered =
      selectedDocId === 'ALL'
        ? allItems
        : allItems.filter((i) => i.document_id === selectedDocId);
    setDocItems(filtered);
    setCurrentIndex((index) => Math.min(index, Math.max(0, filtered.length - 1)));
  }, [allItems, selectedDocId]);

  // ── Unique documents in the queue ──────────────────────────────────────
  const uniqueDocs = [...new Map(allItems.map((i) => [i.document_id, i])).entries()].map(
    ([docId, item]) => ({ docId, count: allItems.filter((x) => x.document_id === docId).length })
  );

  // ── Load context whenever the current item changes ──────────────────────
  const currentItem = docItems[currentIndex] || null;

  useEffect(() => {
    if (!currentItem) {
      setContext(null);
      setImgSrc(null);
      return;
    }

    let cancelled = false;

    const loadContext = async () => {
      setIsLoadingContext(true);
      // Clear the previous field immediately so the image and value never
      // appear out of sync while the next evidence region is loading.
      setContext(null);
      setImgLoaded(false);
      setImgError(false);
      try {
        const ctx = await fetchReviewContext(currentItem.id);
        if (!cancelled) {
          setContext(ctx);
          // Build image URL: prefer the /image endpoint (crops to bbox)
          const imageUrl = getReviewImageUrl(currentItem.id, showFullPage);
          setImgSrc(imageUrl);
        }
      } catch (err) {
        if (!cancelled) {
          // Fallback: try serving the raw document directly
          if (currentItem.document_id) {
            try {
              const fallbackCtx = await fetchReviewContext(currentItem.id);
              if (!cancelled && fallbackCtx?.raw_uri) {
                setContext(fallbackCtx);
                setImgSrc(getDocumentStaticUrl(fallbackCtx.raw_uri));
              }
            } catch (_) {
              setContext(null);
              setImgSrc(null);
            }
          }
        }
      } finally {
        if (!cancelled) setIsLoadingContext(false);
      }
    };

    loadContext();
    return () => { cancelled = true; };
  }, [currentItem?.id, showFullPage]);

  // Update image src when full-page toggle changes
  useEffect(() => {
    if (currentItem) {
      setImgLoaded(false);
      setImgSrc(getReviewImageUrl(currentItem.id, showFullPage));
    }
  }, [showFullPage]);

  // ── Toast helper ───────────────────────────────────────────────────────
  const showToast = (msg, type = 'success') => {
    setToastMsg({ msg, type });
    setTimeout(() => setToastMsg(null), 2500);
  };

  // ── Action handlers ────────────────────────────────────────────────────
  const handleAccept = async (correctedValue) => {
    if (!currentItem || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await submitReviewAction(currentItem.id, 'approve', correctedValue, 'reviewer-ui');
      showToast(
        correctedValue !== null
          ? `✏️ "${currentItem.field_name}" corrected & approved`
          : `✅ "${currentItem.field_name}" accepted`
      );
      setReviewedToday((n) => n + 1);
      // Remove from list and advance
      setAllItems((prev) => prev.filter((i) => i.id !== currentItem.id));
    } catch (err) {
      showToast(err.response?.data?.detail || 'Action failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!currentItem || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await submitReviewAction(currentItem.id, 'reject', null, 'reviewer-ui');
      showToast(`❌ "${currentItem.field_name}" rejected`, 'warn');
      setReviewedToday((n) => n + 1);
      setAllItems((prev) => prev.filter((i) => i.id !== currentItem.id));
    } catch (err) {
      showToast(err.response?.data?.detail || 'Action failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePrev = useCallback(() => setCurrentIndex((i) => Math.max(0, i - 1)), []);
  const handleNext = useCallback(() => setCurrentIndex((i) => Math.min(docItems.length - 1, i + 1)), [docItems.length]);

  // Elapsed review time display
  const elapsedSec = Math.floor((Date.now() - startTimeRef.current) / 1000);
  const elapsedStr =
    elapsedSec >= 60
      ? `${Math.floor(elapsedSec / 60)}m ${elapsedSec % 60}s`
      : `${elapsedSec}s`;

  // ── Bounding box overlay calculation ─────────────────────────────────
  // Passed to the image container as a percentage-based absolutely positioned div
  const bbox = context?.bounding_box;

  // ── Render ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="rq-loading-state">
        <RefreshCw size={32} className="spin" color="var(--primary-cyan)" />
        <p>Loading review queue…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rq-loading-state">
        <AlertTriangle size={32} color="var(--accent-rose)" />
        <p style={{ color: 'var(--accent-rose)' }}>{error}</p>
        <button className="btn btn-primary" onClick={loadQueue} style={{ marginTop: '1rem' }}>
          Retry
        </button>
      </div>
    );
  }

  if (allItems.length === 0) {
    return (
      <div className="rq-empty-state">
        <div className="rq-empty-icon">
          <InboxIcon size={48} color="var(--primary-cyan)" />
        </div>
        <h2>Review Queue is Empty</h2>
        <p>All fields are at or above the confidence threshold — no manual review needed.</p>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
          Upload more documents or lower the confidence threshold to populate the queue.
        </p>
        <button className="btn btn-secondary" onClick={loadQueue} style={{ marginTop: '1.5rem' }}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="rq-root">
      {/* ── Header bar ── */}
      <div className="rq-header">
        <div className="rq-header-left">
          <div className="rq-header-icon">
            <ClipboardCheck size={22} color="var(--primary-cyan)" />
          </div>
          <div>
            <h2 className="rq-header-title">Pending Review Queue</h2>
            <p className="rq-header-sub">Story 3.1 · Side-by-Side Field Verification</p>
          </div>
        </div>

        <div className="rq-stats-strip">
          <div className="rq-stat">
            <AlertTriangle size={14} color="#f59e0b" />
            <span><strong>{allItems.length}</strong> pending</span>
          </div>
          <div className="rq-stat">
            <CheckCircle2 size={14} color="#10b981" />
            <span><strong>{reviewedToday}</strong> reviewed this session</span>
          </div>
          <div className="rq-stat">
            <Clock size={14} color="var(--text-dim)" />
            <span>{elapsedStr} elapsed</span>
          </div>
          <button className="btn btn-secondary rq-refresh-btn" onClick={loadQueue} title="Refresh queue">
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* ── Document selector ── */}
      <div className="rq-doc-selector-wrap">
        <div className="rq-doc-selector-label">Filter by document:</div>
        <div className="rq-doc-selector-scroll">
          <button
            className={`rq-doc-chip ${selectedDocId === 'ALL' ? 'active' : ''}`}
            onClick={() => setSelectedDocId('ALL')}
          >
            All Documents
            <span className="rq-doc-chip-count">{allItems.length}</span>
          </button>
          {uniqueDocs.map(({ docId, count }) => {
            const sample = allItems.find((i) => i.document_id === docId);
            const label = docId.slice(0, 8) + '…';
            return (
              <button
                key={docId}
                className={`rq-doc-chip ${selectedDocId === docId ? 'active' : ''}`}
                onClick={() => setSelectedDocId(docId)}
                title={docId}
              >
                {label}
                <span className="rq-doc-chip-count">{count}</span>
              </button>
            );
          })}
        </div>
        {selectedDocId !== 'ALL' && (
          <button 
            className="btn btn-secondary" 
            style={{ marginLeft: '1rem', whiteSpace: 'nowrap' }}
            onClick={async () => {
              const pid = window.prompt("Enter Patient ID to link this document:");
              if (pid) {
                try {
                  const { linkDocumentToPatient } = await import('../services/api');
                  await linkDocumentToPatient(selectedDocId, pid);
                  setToastMsg({ msg: `Document linked to patient ${pid}`, type: 'success' });
                  setTimeout(() => setToastMsg(null), 2500);
                } catch (err) {
                  setToastMsg({ msg: err.response?.data?.detail || 'Link failed', type: 'error' });
                  setTimeout(() => setToastMsg(null), 2500);
                }
              }
            }}
          >
            Link to Patient
          </button>
        )}
      </div>

      {/* ── Split pane ── */}
      <div className="rq-split-pane">
        {/* ── Left: Document Image Viewer ── */}
        <div className="rq-image-panel">
          <div className="rq-image-toolbar">
            <span className="rq-image-toolbar-label">
              {showFullPage ? 'Full Page View' : 'Field Region'}
            </span>
            <div className="rq-image-toolbar-actions">
              <button
                className="rq-img-btn"
                onClick={() => setShowFullPage((v) => !v)}
                title={showFullPage ? 'Show cropped field region' : 'Show full document page'}
              >
                <Maximize2 size={14} />
                {showFullPage ? 'Crop to Field' : 'Full Page'}
              </button>
              <button
                className="rq-img-btn"
                onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
                title="Zoom in"
                disabled={zoom >= 3}
              >
                <ZoomIn size={14} />
              </button>
              <button
                className="rq-img-btn"
                onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
                title="Zoom out"
                disabled={zoom <= 0.5}
              >
                <ZoomOut size={14} />
              </button>
              <button
                className="rq-img-btn"
                onClick={() => setZoom(1.0)}
                title="Reset zoom"
              >
                <RotateCcw size={13} />
              </button>
            </div>
          </div>

          <div className="rq-image-viewport">
            {isLoadingContext && (
              <div className="rq-image-loader">
                <RefreshCw size={24} className="spin" color="var(--primary-cyan)" />
                <span>Loading image…</span>
              </div>
            )}

            {imgSrc && (
              <div
                className="rq-image-zoom-wrap"
                style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
              >
                <div className="rq-image-container" style={{ position: 'relative', display: 'inline-block' }}>
                  <img
                    key={imgSrc}
                    src={imgSrc}
                    alt="Document region"
                    className={`rq-document-image ${imgLoaded ? 'loaded' : ''}`}
                    onLoad={() => { setImgLoaded(true); setImgError(false); }}
                    onError={() => { setImgError(true); setImgLoaded(true); }}
                    draggable={false}
                  />

                  {/* Bounding box highlight overlay — shown only on full-page view with a valid bbox */}
                  {showFullPage && bbox && imgLoaded && (
                    <div
                      className="rq-bbox-overlay"
                      style={{
                        left: `${bbox.x * 100}%`,
                        top: `${bbox.y * 100}%`,
                        width: `${bbox.width * 100}%`,
                        height: `${bbox.height * 100}%`,
                      }}
                    />
                  )}
                </div>

                {imgError && (
                  <div className="rq-image-error">
                    <AlertTriangle size={20} color="#f59e0b" />
                    <span>Could not load document image. The file may still be processing.</span>
                  </div>
                )}
              </div>
            )}

            {!imgSrc && !isLoadingContext && (
              <div className="rq-image-placeholder">
                <FileTextIcon size={40} style={{ opacity: 0.3 }} />
                <span>No image available</span>
              </div>
            )}
          </div>

          {/* Field label overlay at bottom of image panel */}
          {context && (
            <div className="rq-image-field-label">
              <span className="rq-image-field-tag">Field:</span>
              <span>{context.field_name}</span>
              {context.document_filename && (
                <span className="rq-image-doc-name">· {context.document_filename}</span>
              )}
            </div>
          )}
        </div>

        {/* ── Right: Field Review Panel ── */}
        <div className="rq-review-panel">
          {docItems.length === 0 ? (
            <div className="rq-review-empty">
              <CheckCircle2 size={32} color="#10b981" />
              <p>All fields in this document are reviewed!</p>
            </div>
          ) : (
            <ReviewFieldCard
              item={context || currentItem}
              index={currentIndex}
              total={docItems.length}
              onAccept={handleAccept}
              onReject={handleReject}
              onPrev={handlePrev}
              onNext={handleNext}
              isSubmitting={isSubmitting}
            />
          )}
        </div>
      </div>

      {/* ── Toast notification ── */}
      {toastMsg && (
        <div
          className={`rq-toast ${toastMsg.type === 'error' ? 'rq-toast-error' : toastMsg.type === 'warn' ? 'rq-toast-warn' : 'rq-toast-success'}`}
        >
          {toastMsg.msg}
        </div>
      )}
    </div>
  );
}

// Inline placeholder icon (fallback if Lucide doesn't export FileTextIcon)
function FileTextIcon({ size, style }) {
  return <div style={{ width: size, height: size, ...style }} />;
}
