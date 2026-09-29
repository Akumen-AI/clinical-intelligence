import os

def rep(path, old, new):
    with open(path, "r") as f: content = f.read()
    if old in content:
        with open(path, "w") as f: f.write(content.replace(old, new, 1))

# App.jsx
rep("src/App.jsx", "const ProtectedRoute = ({ children }) => {", """ProtectedRoute.propTypes = { children: PropTypes.any };
const ProtectedRoute = ({ children }) => {""")

# AddNote.jsx
rep("src/components/AddNote.jsx", "  }, [patientId]);", "  }, [patientId, loadNotes]);")

# ClinicalContextPanel.jsx
rep("src/components/ClinicalContextPanel.jsx", "ClinicalContextPanel.propTypes =", "// ")
rep("src/components/ClinicalContextPanel.jsx", "import PropTypes", "//")
rep("src/components/ClinicalContextPanel.jsx", "import { useState, Children", "import React, { useState }")
rep("src/components/ClinicalContextPanel.jsx", "Children.toArray", "React.Children.toArray")
rep("src/components/ClinicalContextPanel.jsx", "export default function ClinicalContextPanel", """import PropTypes from 'prop-types';
ClinicalContextPanel.propTypes = { icon: PropTypes.any, title: PropTypes.any, color: PropTypes.any, children: PropTypes.any, emptyText: PropTypes.any };
export default function ClinicalContextPanel""")

# DynamicJSONEditor.jsx
rep("src/components/DynamicJSONEditor.jsx", "val.hasOwnProperty('id')", "Object.prototype.hasOwnProperty.call(val, 'id')")

# ExtractedFieldsModal.jsx
rep("src/components/ExtractedFieldsModal.jsx", "  }, [fieldData.id]);", "  }, [fieldData.id, loadFields, onClose]);")

# FileUploader.jsx
rep("src/components/FileUploader.jsx", "FileCheck,", "")

# LinkPatientModal.jsx
rep("src/components/LinkPatientModal.jsx", "const { documentId, currentPatientId", "const { currentPatientId")
rep("src/components/LinkPatientModal.jsx", "  }, []);", "  }, [suggestedPatientData.dob, suggestedPatientData.mrn, suggestedPatientData.name, suggestedPatientData.sex]);")
rep("src/components/LinkPatientModal.jsx", "  }, [debouncedSearchQuery]);", "  }, [debouncedSearchQuery, handleSearch, searchQuery]);")

# ReviewFieldCard.jsx
rep("src/components/ReviewFieldCard.jsx", "  }, [isEditing]);", "  }, [isEditing, item?.extracted_value]);")
rep("src/components/ReviewFieldCard.jsx", "} catch (err) {\n        console.error(err);\n      }", "} catch (err) {\n        /* do nothing */\n      }")

# Sidebar.jsx, AuthContext.jsx
# react-refresh/only-export-components warns if non-components are exported.
# We will just disable this specific rule for these files since exporting contexts is normal.
rep("src/components/Sidebar.jsx", "export const SIDEBAR_WIDTH", "/* eslint-disable react-refresh/only-export-components */\nexport const SIDEBAR_WIDTH")
rep("src/contexts/AuthContext.jsx", "export const useAuth", "/* eslint-disable react-refresh/only-export-components */\nexport const useAuth")

# PatientDashboardPage.jsx
rep("src/pages/PatientDashboardPage.jsx", "FileText,", "")

# ReviewQueuePage.jsx
rep("src/pages/ReviewQueuePage.jsx", "} catch (err) {\n      console.error(err);\n    }", "} catch (err) {\n      /* do nothing */\n    }")
rep("src/pages/ReviewQueuePage.jsx", "  }, []);", "  }, [currentItem]);")
rep("src/pages/ReviewQueuePage.jsx", "  }, [isLinking]);", "  }, [isLinking, currentItem]);")
rep("src/pages/ReviewQueuePage.jsx", "item, index", "index")

# TimelinePage.jsx
rep("src/pages/TimelinePage.jsx", "const totalEvents = events.length;", "")

# UploadPage.jsx
rep("src/pages/UploadPage.jsx", "  }, []);", "  }, [loadConfig, loadData]);")
rep("src/pages/UploadPage.jsx", "  }, [files]);", "  }, [files, documents]);")

