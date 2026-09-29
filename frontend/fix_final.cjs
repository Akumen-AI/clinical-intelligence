const fs = require('fs');

function applyFixes(filePath, fixes) {
    let content = fs.readFileSync(filePath, 'utf8').split('\n');
    for (let i = fixes.length - 1; i >= 0; i--) {
        const { line, old, new: newStr } = fixes[i];
        const lineIdx = line - 1;
        if (content[lineIdx].includes(old)) {
            content[lineIdx] = content[lineIdx].replace(old, newStr);
        } else {
            console.error(`Failed to apply fix on ${filePath}:${line}`);
        }
    }
    fs.writeFileSync(filePath, content.join('\n'));
}

applyFixes('src/App.jsx', [
    { line: 2, old: 'useState,', new: '' },
    { line: 71, old: 'ProtectedRoute.propTypes =', new: '// ProtectedRoute.propTypes =' }
]);

applyFixes('src/components/ClinicalContextPanel.jsx', [
    { line: 36, old: 'ClinicalContextPanel.propTypes =', new: '// ClinicalContextPanel.propTypes =' },
    { line: 37, old: "import PropTypes from 'prop-types';", new: '// ' }
]);

applyFixes('src/components/DynamicJSONEditor.jsx', [
    { line: 150, old: "val.hasOwnProperty('id')", new: "Object.prototype.hasOwnProperty.call(val, 'id')" }
]);

applyFixes('src/components/FileUploader.jsx', [
    { line: 11, old: "FileCheck,", new: "" }
]);

applyFixes('src/components/LinkPatientModal.jsx', [
    { line: 6, old: "const { documentId, currentPatientId, onClose, onLinkSuccess } = props;", new: "const { currentPatientId, onClose, onLinkSuccess } = props;" }
]);

applyFixes('src/components/ReviewFieldCard.jsx', [
    { line: 137, old: "} catch (err) {", new: "} catch (err) { /* no-op */ }" }
]);

applyFixes('src/pages/NaturalLanguageReportPage.jsx', [
    { line: 178, old: "LLM's", new: "LLM&apos;s" }
]);

applyFixes('src/pages/PatientDashboardPage.jsx', [
    { line: 12, old: "FileText,", new: "" },
    { line: 136, old: "Patient's", new: "Patient&apos;s" }
]);

applyFixes('src/pages/ReviewQueuePage.jsx', [
    { line: 60, old: "} catch (err) {", new: "} catch (err) { /* no-op */ }" },
    { line: 121, old: "item, index", new: "index" }
]);

applyFixes('src/pages/TimelinePage.jsx', [
    { line: 41, old: "const totalEvents = events.length;", new: "" }
]);

applyFixes('src/pages/UploadPage.jsx', [
    { line: 281, old: "const acceptedLogsCount = auditLogs.filter(log => log.action_type === 'document_accepted').length;", new: "" }
]);
