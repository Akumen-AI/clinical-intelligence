import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
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
  InboxIcon,
  FileText,
} from 'lucide-react';
import ReviewFieldCard from '../components/ReviewFieldCard';
import LinkPatientModal from '../components/LinkPatientModal';
import {
  fetchPendingReviews,
  fetchReviewContext,
  submitReviewAction,
  getReviewImageUrl,
  getDocumentStaticUrl,
  fetchDocuments,
} from '../services/api';

export default function ReviewQueuePage() {
  const [viewMode, setViewMode] = useState('list');
  const [documents, setDocuments] = useState([]);
  const [allItems, setAllItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedDocId, setSelectedDocId] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [context, setContext] = useState(null);
  const [isLoadingContext, setIsLoadingContext] = useState(false);

  const [imgSrc, setImgSrc] = useState(null);
  const [imgError, setImgError] = useState(false);
  const [showFullPage, setShowFullPage] = useState(false);
  const [zoom, setZoom] = useState(1.0);
  const [imgLoaded, setImgLoaded] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
  
  const patientAssignmentStr = allItems.find(i => i.document_id === selectedDocId && i.field_name === 'patient_assignment')?.extracted_value;
  const patientIdStr = allItems.find(i => i.document_id === selectedDocId && i.field_name === 'patient_identifier')?.extracted_value;

  const suggestedPatientData = useMemo(() => {
    let data = { name: '', mrn: '', dob: '', sex: '' };
    if (patientAssignmentStr) {
      try {
        const parsed = JSON.parse(patientAssignmentStr);
        if (parsed.name) data.name = parsed.name;
        if (parsed.dob) data.dob = parsed.dob;
        if (parsed.gender) data.sex = parsed.gender;
        if (parsed.patient_id) data.mrn = parsed.patient_id;
      } catch (e) {}
    } else if (patientIdStr) {
      try {
        const parsed = JSON.parse(patientIdStr);
        if (parsed.patient_id) data.mrn = parsed.patient_id;
        if (parsed.name) data.name = parsed.name;
      } catch (e) {
        data.name = patientIdStr;
      }
    }
    return data;
  }, [patientAssignmentStr, patientIdStr]);

  const [reviewedToday, setReviewedToday] = useState(0);
  const startTimeRef = useRef(Date.now());

  const loadQueue = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [reviewsData, docsData] = await Promise.all([
        fetchPendingReviews(null, 1, 100),
        fetchDocuments()
      ]);
      setAllItems(reviewsData.items || []);
      setDocuments(docsData || []);
    } catch (err) {
      const raw = err.response?.data?.detail;
      let msg = 'Failed to load review queue';
      if (typeof raw === 'string') msg = raw;
      else if (Array.isArray(raw)) msg = raw.map((e) => e.msg || JSON.stringify(e)).join('; ');
      else if (raw) msg = JSON.stringify(raw);
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const docItems = useMemo(() => {
    if (selectedDocId === 'ALL') return allItems;
    if (!selectedDocId) return [];
    return allItems.filter((i) => i.document_id === selectedDocId);
  }, [allItems, selectedDocId]);

  useEffect(() => {
    setCurrentIndex((index) => Math.min(index, Math.max(0, docItems.length - 1)));
  }, [docItems.length]);

  const uniqueDocs = [...new Map(allItems.map((i) => [i.document_id, i])).entries()].map(
    ([docId, item]) => {
      const dItems = allItems.filter((x) => x.document_id === docId);
      const isPatientAssignment = dItems.some(x => x.field_name === 'patient_assignment');
      return { 
        docId, 
        count: dItems.length,
        isPatientAssignment
      };
    }
  );

  useEffect(() => {
    if (viewMode === 'review' && selectedDocId && docItems.length === 0) {
      setViewMode('list');
      setSelectedDocId(null);
      setToastMsg({ msg: '🎉 All fields for this document have been reviewed!', type: 'success' });
      setTimeout(() => setToastMsg(null), 2500);
    }
  }, [docItems.length, viewMode, selectedDocId]);

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
      setContext(null);
      setImgLoaded(false);
      setImgError(false);
      try {
        const ctx = await fetchReviewContext(currentItem.id);
        if (!cancelled) {
          setContext(ctx);
          const imageUrl = getReviewImageUrl(currentItem.id, showFullPage);
          setImgSrc(imageUrl);
        }
      } catch (err) {
        if (!cancelled) {
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

  useEffect(() => {
    if (currentItem) {
      setImgLoaded(false);
      setImgSrc(getReviewImageUrl(currentItem.id, showFullPage));
    }
  }, [showFullPage]);

  const showToast = (msg, type = 'success') => {
    setToastMsg({ msg, type });
    setTimeout(() => setToastMsg(null), 2500);
  };

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

  const elapsedSec = Math.floor((Date.now() - startTimeRef.current) / 1000);
  const elapsedStr =
    elapsedSec >= 60
      ? `${Math.floor(elapsedSec / 60)}m ${elapsedSec % 60}s`
      : `${elapsedSec}s`;

  const bbox = context?.bounding_box;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-on-surface-variant">
        <RefreshCw size={32} className="animate-spin mb-4 text-primary" />
        <p>Loading review queue…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-error">
        <AlertTriangle size={32} className="mb-4" />
        <p>{error}</p>
        <button className="mt-4 px-4 py-2 bg-primary text-on-primary rounded-lg font-semibold hover:bg-primary/90 transition-colors" onClick={loadQueue}>
          Retry
        </button>
      </div>
    );
  }

  // Early return for empty state removed so the header is always rendered.

  return (
    <div className="app-container flex-1 flex flex-col min-h-0">
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <ClipboardCheck size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Pending Review Queue</h1>
            <p>Human-in-the-Loop Verification</p>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-surface-container-high px-4 py-2 rounded-xl border border-outline-variant/20">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle size={16} className="text-amber-500" />
            <span className="text-on-surface"><span className="text-amber-500">{allItems.length}</span> pending</span>
          </div>
          <div className="w-px h-4 bg-outline-variant/30 mx-2"></div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <CheckCircle2 size={16} className="text-emerald-500" />
            <span className="text-on-surface"><span className="text-emerald-500">{reviewedToday}</span> reviewed this session</span>
          </div>
          <div className="w-px h-4 bg-outline-variant/30 mx-2"></div>
          <div className="flex items-center gap-2 text-sm text-on-surface-variant font-medium">
            <Clock size={16} />
            <span>{elapsedStr}</span>
          </div>
          <button className="btn btn-icon ml-2" onClick={loadQueue} title="Refresh queue">
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      {viewMode === 'list' ? (
        <div className="grid gap-4 mt-2">
          {allItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-8 bg-surface-container rounded-2xl border border-outline-variant/20 mt-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
                <InboxIcon size={32} className="text-primary" />
              </div>
              <h2 className="text-headline-md font-headline-md text-on-surface mb-2">Review Queue is Empty</h2>
              <p className="text-body-lg font-body-lg text-on-surface-variant mb-1">All fields are at or above the confidence threshold — no manual review needed.</p>
              <p className="text-sm text-on-surface-variant/70 mb-6">Upload more documents or lower the confidence threshold to populate the queue.</p>
              <button className="flex items-center gap-2 px-4 py-2 bg-surface-variant text-on-surface rounded-lg font-semibold border border-outline-variant/30 hover:bg-surface-variant/80 transition-colors" onClick={loadQueue}>
                <RefreshCw size={16} /> Refresh
              </button>
            </div>
          ) : (
            uniqueDocs.map(({ docId, count, isPatientAssignment }) => {
              const doc = documents.find(d => d.document_id === docId);
              const filename = doc ? doc.filename : (docId.slice(0, 8) + '…');
              return (
                <div key={docId} className="flex justify-between items-center p-5 bg-surface-container rounded-xl border border-outline-variant/20 hover:border-outline-variant/40 transition-colors">
                  <div>
                    <h3 className="flex items-center gap-2 text-lg font-semibold text-on-surface mb-2">
                      <FileText size={20} className="text-primary" />
                      {filename}
                    </h3>
                    <div className="flex gap-4 text-sm font-medium">
                      {isPatientAssignment ? (
                        <span className="flex items-center gap-1.5 text-error">
                          <AlertTriangle size={16} /> Needs Patient Assignment
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-amber-500">
                          <ZoomIn size={16} /> Low Confidence Data ({count} fields)
                        </span>
                      )}
                    </div>
                  </div>
                  <button 
                    className="px-5 py-2.5 bg-gradient-to-r from-primary to-secondary text-white rounded-lg font-semibold shadow-lg shadow-primary/20 hover:opacity-90 transition-opacity"
                    onClick={() => {
                      setSelectedDocId(docId);
                      setViewMode('review');
                    }}
                  >
                    Start Review
                  </button>
                </div>
              );
            })
          )}
        </div>
      ) : (
        <div className="flex flex-col h-full flex-grow">
          <div className="mb-4">
            <button 
              className="flex items-center gap-2 px-4 py-2 bg-surface-variant text-on-surface rounded-lg font-semibold border border-outline-variant/30 hover:bg-surface-variant/80 transition-colors text-sm"
              onClick={() => { setViewMode('list'); setSelectedDocId(null); }}
            >
              <RotateCcw size={16} className="-rotate-45" /> Back to Queue
            </button>
          </div>

          <LinkPatientModal 
            isOpen={isLinkModalOpen}
            onClose={() => setIsLinkModalOpen(false)}
            documentId={selectedDocId}
            suggestedPatientData={suggestedPatientData}
            onLink={async (payload) => {
              setIsLinkModalOpen(false);
              try {
                const { default: api } = await import('../services/api');
                await api.post(`/documents/${selectedDocId}/link-patient`, payload);
                setToastMsg({ msg: `Document linked to patient successfully!`, type: 'success' });
                setTimeout(() => setToastMsg(null), 2500);
              } catch (err) {
                setToastMsg({ msg: err.response?.data?.detail || 'Link failed', type: 'error' });
                setTimeout(() => setToastMsg(null), 2500);
              }
            }}
          />

          {/* Split Pane Container */}
          <div className="flex flex-col lg:flex-row gap-6 flex-grow min-h-0">
            
            {/* Left: Document Image Viewer */}
            <div className="flex flex-col flex-1 bg-surface-container rounded-2xl border border-outline-variant/20 overflow-hidden relative">
              <div className="flex justify-between items-center p-3 border-b border-outline-variant/10 bg-surface-container-high">
                <span className="text-sm font-semibold text-on-surface-variant px-2">
                  {showFullPage ? 'Full Page View' : 'Field Region View'}
                </span>
                <div className="flex items-center gap-1">
                  <button className="p-1.5 rounded text-on-surface-variant hover:bg-surface-variant hover:text-on-surface transition-colors flex items-center gap-1.5 text-xs font-semibold mr-2" onClick={() => setShowFullPage((v) => !v)}>
                    <Maximize2 size={14} /> {showFullPage ? 'Crop to Field' : 'Full Page'}
                  </button>
                  <div className="w-px h-4 bg-outline-variant/30 mx-1"></div>
                  <button className="p-1.5 rounded text-on-surface-variant hover:bg-surface-variant hover:text-on-surface transition-colors" onClick={() => setZoom((z) => Math.min(3, z + 0.25))} disabled={zoom >= 3}>
                    <ZoomIn size={16} />
                  </button>
                  <button className="p-1.5 rounded text-on-surface-variant hover:bg-surface-variant hover:text-on-surface transition-colors" onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} disabled={zoom <= 0.5}>
                    <ZoomOut size={16} />
                  </button>
                  <button className="p-1.5 rounded text-on-surface-variant hover:bg-surface-variant hover:text-on-surface transition-colors" onClick={() => setZoom(1.0)}>
                    <RotateCcw size={14} />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-auto p-4 bg-surface-container-highest/20 relative flex items-center justify-center min-h-[400px]">
                {isLoadingContext && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface-container/50 z-10">
                    <RefreshCw size={24} className="animate-spin text-primary mb-2" />
                    <span className="text-sm font-medium text-on-surface-variant">Loading image…</span>
                  </div>
                )}

                {imgSrc ? (
                  <div className="origin-top-left transition-transform duration-200" style={{ transform: `scale(${zoom})` }}>
                    <div className="relative inline-block shadow-2xl rounded overflow-hidden">
                      <img
                        key={imgSrc}
                        src={imgSrc}
                        alt="Document region"
                        className={`max-w-none transition-opacity duration-300 ${imgLoaded ? 'opacity-100' : 'opacity-0'}`}
                        style={{ maxHeight: showFullPage ? 'none' : '400px' }}
                        onLoad={() => { setImgLoaded(true); setImgError(false); }}
                        onError={() => { setImgError(true); setImgLoaded(true); }}
                        draggable={false}
                      />
                      {showFullPage && bbox && imgLoaded && (
                        <div
                          className="absolute border-2 border-primary bg-primary/20 pointer-events-none rounded-sm"
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
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-amber-500 bg-surface-container/90">
                        <AlertTriangle size={32} className="mb-2" />
                        <span className="text-sm font-medium">Could not load document image.</span>
                      </div>
                    )}
                  </div>
                ) : !isLoadingContext ? (
                  <div className="flex flex-col items-center text-on-surface-variant/50">
                    <FileText size={48} className="mb-2 opacity-50" />
                    <span className="text-sm font-semibold">No image available</span>
                  </div>
                ) : null}
              </div>

              {context && (
                <div className="absolute bottom-4 left-4 right-4 bg-surface-container-high/90 backdrop-blur border border-outline-variant/30 p-3 rounded-lg flex justify-between items-center shadow-lg">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-1 bg-primary/20 text-primary text-xs font-bold rounded uppercase">Target Field</span>
                    <span className="font-semibold text-on-surface">{context.field_name}</span>
                  </div>
                  {context.document_filename && (
                    <span className="text-sm text-on-surface-variant truncate max-w-[50%]">{context.document_filename}</span>
                  )}
                </div>
              )}
            </div>

            {/* Right: Field Review Panel */}
            <div className="flex flex-col w-full lg:w-[450px] shrink-0">
              {docItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full bg-surface-container rounded-2xl border border-outline-variant/20 p-8 text-center">
                  <CheckCircle2 size={48} className="text-emerald-500 mb-4" />
                  <p className="text-xl font-semibold text-on-surface mb-2">Document Complete!</p>
                  <p className="text-on-surface-variant">All fields in this document are reviewed.</p>
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
        </div>
      )}

      {/* Toast Notification */}
      {toastMsg && (
        <div className={`fixed bottom-6 right-6 px-6 py-3 rounded-xl shadow-2xl text-sm font-bold flex items-center gap-2 z-50 animate-fade-in-up border ${
          toastMsg.type === 'error' ? 'bg-error-container text-error border-error/30' : 
          toastMsg.type === 'warn' ? 'bg-amber-500/20 text-amber-500 border-amber-500/30' : 
          'bg-emerald-500/20 text-emerald-500 border-emerald-500/30'
        }`}>
          {toastMsg.msg}
        </div>
      )}
    </div>
  );
}
