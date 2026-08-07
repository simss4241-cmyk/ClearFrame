document.addEventListener("DOMContentLoaded", () => {
    let currentReport = null;
    let activeDepartment = "SOUND_MUSIC";

    // UI Element References
    const btnDemo = document.getElementById("btn-demo");
    const scriptFileInput = document.getElementById("script-file-input");
    const scriptTitle = document.getElementById("script-title");
    const scriptContent = document.getElementById("script-content");
    const radarStatus = document.getElementById("radar-status");

    const metricTotal = document.getElementById("metric-total");
    const metricRed = document.getElementById("metric-red");
    const metricAmber = document.getElementById("metric-amber");
    const metricGreen = document.getElementById("metric-green");

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

    // Run Demo Scene
    btnDemo.addEventListener("click", async () => {
        setLoadingState(true);
        try {
            const res = await fetch("/api/clearance/demo");
            if (!res.ok) throw new Error("Failed to execute clearance demo.");
            currentReport = await res.json();
            renderReport(currentReport);
            addFeedLog("Analysis pipeline complete. Live Parallel Monitors registered.");
        } catch (err) {
            alert(err.message);
        } finally {
            setLoadingState(false);
        }
    });

    // Upload Script File
    scriptFileInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setLoadingState(true);
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/clearance/analyze", {
                method: "POST",
                body: formData
            });
            if (!res.ok) throw new Error("Failed to analyze uploaded script.");
            currentReport = await res.json();
            renderReport(currentReport);
            addFeedLog(`Uploaded script parsed: ${file.name}`);
        } catch (err) {
            alert(err.message);
        } finally {
            setLoadingState(false);
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

    function setLoadingState(loading) {
        if (loading) {
            radarStatus.textContent = "Analyzing Script...";
            btnDemo.disabled = true;
        } else {
            radarStatus.textContent = "Ready";
            btnDemo.disabled = false;
        }
    }

    function renderReport(report) {
        scriptTitle.textContent = report.title;

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
                    
                    // Simple replacement for matching snippet keywords
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
                <div class="card-header">
                    <div class="card-title-group">
                        <h4>${escapeHtml(el.text)}</h4>
                        <span class="card-subtype">${escapeHtml(el.subtype)}</span>
                    </div>
                    <div class="verdict-pill ${ratingClass}">
                        ${verdict.rating} <span class="rule-id">[${verdict.rule_id}]</span>
                    </div>
                </div>

                <div class="context-quote">"${escapeHtml(el.context_snippet)}"</div>

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
            return "";
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
