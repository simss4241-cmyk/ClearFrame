document.addEventListener("DOMContentLoaded", () => {
    let currentReport = null;
    let activeDepartment = "SOUND_MUSIC";

    // UI Element References
    const btnDemo = document.getElementById("btn-demo");
    const scriptFileInput = document.getElementById("script-file-input");
    const scriptFilename = document.getElementById("script-filename");
    const scriptHash = document.getElementById("script-hash");
    const scriptContent = document.getElementById("script-content");
    const radarStatus = document.getElementById("radar-status");

    const metricTotal = document.getElementById("metric-total");
    const metricRed = document.getElementById("metric-red");
    const metricAmber = document.getElementById("metric-amber");
    const metricGreen = document.getElementById("metric-green");

    const errorBannerWrapper = document.getElementById("error-banner-wrapper");
    const deptTabs = document.getElementById("dept-tabs");
    const pluginWorkspace = document.getElementById("plugin-workspace");

    const watchDrawer = document.getElementById("watch-drawer");
    const drawerToggle = document.getElementById("drawer-toggle");
    const monitorCount = document.getElementById("monitor-count");
    const monitorFeed = document.getElementById("monitor-feed");

    // Collapsible Drawer Toggle
    drawerToggle.addEventListener("click", () => {
        watchDrawer.classList.toggle("collapsed");
        const toggleIcon = drawerToggle.querySelector(".toggle-icon");
        toggleIcon.textContent = watchDrawer.classList.contains("collapsed") ? "▲" : "▼";
    });

    // Immediate Workspace Reset
    function clearWorkspace(filename = "script.txt") {
        currentReport = null;
        scriptFilename.textContent = filename;
        scriptHash.textContent = "Processing...";
        scriptContent.innerHTML = `<div class="empty-state"><p>⚡ Analyzing <strong>${escapeHtml(filename)}</strong>... Executing Google Cloud Gemini &amp; Parallel Search pipeline.</p></div>`;
        
        radarStatus.textContent = "ANALYZING...";
        radarStatus.className = "radar-status";

        metricTotal.textContent = "0";
        metricRed.textContent = "0";
        metricAmber.textContent = "0";
        metricGreen.textContent = "0";

        errorBannerWrapper.style.display = "none";
        errorBannerWrapper.innerHTML = "";

        document.querySelectorAll(".tab-badge").forEach(b => b.textContent = "0");
        monitorCount.textContent = "0 Active Monitors";

        pluginWorkspace.innerHTML = `<div class="empty-state"><p>Running clearance research... Citations and findings will appear upon completion.</p></div>`;
        monitorFeed.innerHTML = `<div class="feed-item placeholder"><span class="timestamp">${new Date().toLocaleTimeString()}</span><span class="event-text">Initiated script clearance pipeline for ${escapeHtml(filename)}...</span></div>`;
    }

    // Display Fail-Loud Error Banner
    function showErrorBanner(filename, hash, errorMsg) {
        currentReport = null;
        radarStatus.textContent = "RUN INCOMPLETE";
        radarStatus.className = "radar-status error";

        errorBannerWrapper.style.display = "block";
        errorBannerWrapper.innerHTML = `
            <div class="error-banner">
                <h4>⚠️ ANALYSIS FAILED / RUN INCOMPLETE</h4>
                <p>The clearance pipeline encountered an unrecoverable error during execution. <strong>Zero substitute or fallback data was generated.</strong></p>
                <div style="margin-top: 6px; font-family: var(--font-mono); font-size: 11px; opacity: 0.9;">
                    <span>Target File: <strong>${escapeHtml(filename)}</strong></span> | 
                    <span>Run Hash: <strong>${escapeHtml(hash || "N/A")}</strong></span>
                </div>
                <div class="error-details">${escapeHtml(errorMsg)}</div>
            </div>`;

        pluginWorkspace.innerHTML = `
            <div class="empty-state">
                <p style="color: var(--risk-red);">❌ Clearance run incomplete. Fix the underlying credential/API error and resubmit.</p>
            </div>`;

        addFeedLog(`🚨 PIPELINE ERROR: ${errorMsg}`);
    }

    // Run Demo Scene (Explicit Demo Action Only)
    btnDemo.addEventListener("click", async () => {
        clearWorkspace("scene_01.txt");
        btnDemo.disabled = true;

        try {
            const res = await fetch("/api/clearance/demo");
            const data = await res.json();

            if (!res.ok || data.status === "INCOMPLETE_ERROR") {
                const errMsg = data.detail || "Demo execution failed.";
                showErrorBanner(data.filename || "scene_01.txt", data.script_hash || "", errMsg);
                return;
            }

            currentReport = data;
            renderReport(currentReport);
            addFeedLog("Demo analysis pipeline complete. Live Parallel Monitors registered.");
        } catch (err) {
            showErrorBanner("scene_01.txt", "", err.message);
        } finally {
            btnDemo.disabled = false;
        }
    });

    // Upload Script File
    scriptFileInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        clearWorkspace(file.name);
        const formData = new FormData();
        formData.append("file", file);
        formData.append("filename", file.name);

        try {
            const res = await fetch("/api/clearance/analyze", {
                method: "POST",
                body: formData
            });

            const data = await res.json();

            if (!res.ok || data.status === "INCOMPLETE_ERROR") {
                const errMsg = data.detail || "Script analysis failed.";
                showErrorBanner(data.filename || file.name, data.script_hash || "", errMsg);
                return;
            }

            currentReport = data;
            renderReport(currentReport);
            addFeedLog(`Uploaded script parsed cleanly: ${file.name}`);
        } catch (err) {
            showErrorBanner(file.name, "", err.message);
        } finally {
            scriptFileInput.value = "";
        }
    });

    // Tab Router Switch
    deptTabs.addEventListener("click", (e) => {
        const btn = e.target.closest(".tab-btn");
        if (!btn) return;
        const dept = btn.dataset.dept;
        if (!dept) return;

        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeDepartment = dept;
        renderDepartmentCards();
    });

    function renderReport(report) {
        scriptFilename.textContent = report.filename || report.title;
        scriptHash.textContent = report.script_hash ? `Hash: ${report.script_hash}` : `Run: ${report.script_id}`;

        radarStatus.textContent = report.status === "COMPLETE" ? "COMPLETE" : "INCOMPLETE";
        radarStatus.className = report.status === "COMPLETE" ? "radar-status" : "radar-status error";

        // Metrics update
        metricTotal.textContent = report.total_elements;
        metricRed.textContent = report.red_count;
        metricAmber.textContent = report.amber_count;
        metricGreen.textContent = report.green_count;

        // Department tab badges update
        let activeMonitors = 0;
        for (const [deptKey, summary] of Object.entries(report.departments)) {
            const badge = document.getElementById(`badge-${deptKey}`);
            if (badge) badge.textContent = summary.total_elements;
            activeMonitors += (summary.red_count + summary.amber_count);
        }
        monitorCount.textContent = `${activeMonitors} Active Monitors`;

        // Render Script Text with Highlights
        renderScriptText(report);

        // Render Cards for Active Tab
        renderDepartmentCards();
    }

    function renderScriptText(report) {
        if (!report.scenes || report.scenes.length === 0) return;

        let html = "";
        report.scenes.forEach(scene => {
            html += `<div class="scene-heading">${escapeHtml(scene.heading)}</div>`;
            let text = escapeHtml(scene.text);

            // Replace element text occurrences with inline risk pills
            for (const deptKey in report.departments) {
                const summary = report.departments[deptKey];
                summary.elements.forEach(item => {
                    const elText = item.element.text;
                    const rating = item.verdict.rating.toLowerCase();
                    const pillHtml = `<span class="hl-risk ${rating}" data-el-id="${item.element.id}" data-dept="${item.element.department}">${escapeHtml(elText)}</span>`;
                    
                    if (text.includes(elText)) {
                        text = text.split(elText).join(pillHtml);
                    }
                });
            }

            html += `<div class="screenplay-text">${text}</div>`;
        });

        scriptContent.innerHTML = html;

        // Add Click handlers on inline highlights
        scriptContent.querySelectorAll(".hl-risk").forEach(pill => {
            pill.addEventListener("click", () => {
                const dept = pill.dataset.dept;
                const elId = pill.dataset.elId;
                
                // Switch tab
                const tabBtn = document.querySelector(`.tab-btn[data-dept="${dept}"]`);
                if (tabBtn) tabBtn.click();

                // Scroll to card
                setTimeout(() => {
                    const card = document.getElementById(`card-${elId}`);
                    if (card) card.scrollIntoView({ behavior: "smooth", block: "center" });
                }, 100);
            });
        });
    }

    function renderDepartmentCards() {
        if (!currentReport) return;
        const summary = currentReport.departments[activeDepartment];

        if (!summary || !summary.elements || summary.elements.length === 0) {
            pluginWorkspace.innerHTML = `<div class="empty-state"><p>No flagged elements in this department.</p></div>`;
            return;
        }

        let html = "";
        summary.elements.forEach(item => {
            const el = item.element;
            const verdict = item.verdict;
            const finding = item.finding;
            const ratingClass = verdict.rating.toLowerCase();

            html += `
            <div class="clearance-card ${ratingClass}" id="card-${el.id}">
                <div class="card-provenance-bar">
                    <span>📄 Source: <strong>${escapeHtml(currentReport.filename)}</strong></span>
                    <span>Run Hash: <strong>${escapeHtml(currentReport.script_hash || currentReport.script_id)}</strong></span>
                </div>

                <div class="card-header">
                    <div class="card-title-group">
                        <h4>${escapeHtml(el.text)}</h4>
                        <span class="card-subtype">${escapeHtml(el.subtype)}</span>
                    </div>
                    <div class="verdict-pill ${ratingClass}">
                        ${verdict.rating} <span class="rule-id">[${verdict.rule_id}]</span>
                    </div>
                </div>

                <div class="context-quote">"${escapeHtml(el.quoted_source_passage || el.context_snippet)}"</div>

                <div class="rationale-box">
                    <strong>Rule Rationale:</strong> ${escapeHtml(verdict.rationale)}
                </div>

                ${renderBasisSection(finding)}
            </div>`;
        });

        pluginWorkspace.innerHTML = html;
    }

    function renderBasisSection(finding) {
        if (!finding || !finding.basis || finding.basis.length === 0) {
            return `<div class="basis-section"><div class="basis-header"><span>PARALLEL EVIDENTIARY BASIS</span></div><div class="basis-item"><div class="basis-reasoning">No live search evidence retrieved. Evaluated deterministically.</div></div></div>`;
        }

        let basisHtml = "";
        finding.basis.forEach(b => {
            const confPct = Math.round(b.confidence * 100);
            basisHtml += `
            <div class="basis-item">
                <div class="basis-reasoning">${escapeHtml(b.reasoning)}</div>
                <a href="${b.url}" target="_blank" rel="noopener" class="basis-link">🔗 Citation: ${escapeHtml(b.url)}</a>
                <span class="confidence-tag"> (${confPct}% Confidence)</span>
            </div>`;
        });

        return `
        <div class="basis-section">
            <div class="basis-header">
                <span>PARALLEL EVIDENTIARY BASIS</span>
            </div>
            ${basisHtml}
        </div>`;
    }

    function addFeedLog(msg) {
        const time = new Date().toLocaleTimeString();
        const div = document.createElement("div");
        div.className = "feed-item";
        div.innerHTML = `<span class="timestamp">[${time}]</span> <span class="event-text">${escapeHtml(msg)}</span>`;
        monitorFeed.prepend(div);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
});
