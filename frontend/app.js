document.addEventListener("DOMContentLoaded", () => {
    let currentReport = null;
    let loadedFile = null;
    let loadedScriptText = "";
    let activeDepartment = "SOUND_MUSIC";
    let radarBlips = [];
    let radarAnimFrame = null;
    let sweepAngle = 0;
    let isEditMode = false;
    let loadingStepTimer = null;

    // UI Element References
    const btnDemo = document.getElementById("btn-demo");
    const demoFixtureSelect = document.getElementById("demo-fixture-select");
    const scriptFileInput = document.getElementById("script-file-input");
    const btnRunClearance = document.getElementById("btn-run-clearance");
    const btnModeView = document.getElementById("btn-mode-view");
    const btnModeEdit = document.getElementById("btn-mode-edit");
    const scriptStatusDot = document.getElementById("script-status-dot");
    const scriptFilename = document.getElementById("script-filename");
    const scriptContent = document.getElementById("script-content");
    const radarStatus = document.getElementById("radar-status");

    const btnExportToggle = document.getElementById("btn-export-toggle");
    const exportMenu = document.getElementById("export-menu");
    const btnExportTxt = document.getElementById("btn-export-txt");
    const btnExportFdx = document.getElementById("btn-export-fdx");
    const btnExportDocket = document.getElementById("btn-export-docket");

    const telemetryIntegrity = document.getElementById("telemetry-integrity");
    const telemetryIntegrityBadge = document.getElementById("telemetry-integrity-badge");
    const metricRed = document.getElementById("metric-red");
    const metricAmber = document.getElementById("metric-amber");
    const telemetryCorroboration = document.getElementById("telemetry-corroboration");
    const telemetryExhibitsCount = document.getElementById("telemetry-exhibits-count");

    const progGreen = document.getElementById("prog-green");
    const progAmber = document.getElementById("prog-amber");
    const progRed = document.getElementById("prog-red");
    const progLabelGreen = document.getElementById("prog-label-green");
    const progLabelAmber = document.getElementById("prog-label-amber");
    const progLabelRed = document.getElementById("prog-label-red");

    const errorBannerWrapper = document.getElementById("error-banner-wrapper");
    const deptTabs = document.getElementById("dept-tabs");
    const pluginWorkspace = document.getElementById("plugin-workspace");

    const filmReelCursor = document.getElementById("custom-film-reel-cursor");
    window.addEventListener("mousemove", (e) => {
        if (filmReelCursor) {
            filmReelCursor.style.left = `${e.clientX}px`;
            filmReelCursor.style.top = `${e.clientY}px`;
        }
    });

    const watchDrawer = document.getElementById("watch-drawer");
    const drawerToggle = document.getElementById("drawer-toggle");
    const monitorCount = document.getElementById("monitor-count");
    const monitorFeed = document.getElementById("monitor-feed");

    const radarCanvas = document.getElementById("radar-canvas");
    const radarCtx = radarCanvas ? radarCanvas.getContext("2d") : null;

    // Collapsible Drawer Toggle
    drawerToggle.addEventListener("click", () => {
        watchDrawer.classList.toggle("collapsed");
        const toggleIcon = drawerToggle.querySelector(".toggle-icon");
        toggleIcon.textContent = watchDrawer.classList.contains("collapsed") ? "▲" : "▼";
    });

    // Read vs Edit Mode Switcher
    function setEditMode(enableEdit) {
        isEditMode = enableEdit;
        if (btnModeView) btnModeView.classList.toggle("active", !enableEdit);
        if (btnModeEdit) btnModeEdit.classList.toggle("active", enableEdit);

        const page = scriptContent.querySelector(".screenplay-page");
        if (page) {
            page.setAttribute("contenteditable", enableEdit ? "true" : "false");
            page.classList.toggle("edit-mode", enableEdit);
            if (enableEdit) {
                page.focus();
                addFeedLog("Switched to Screenplay Edit Mode. Edits are tracked and autosaved.");
            } else {
                addFeedLog("Switched to Screenplay Read Mode. Click any highlight to inspect exhibits.");
            }
        }
    }

    if (btnModeView) btnModeView.addEventListener("click", () => setEditMode(false));
    if (btnModeEdit) btnModeEdit.addEventListener("click", () => setEditMode(true));

    // Export Dropdown Menu Toggle
    if (btnExportToggle && exportMenu) {
        btnExportToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            exportMenu.classList.toggle("show");
        });

        document.addEventListener("click", () => {
            exportMenu.classList.remove("show");
        });
    }

    // Export Action Handlers
    if (btnExportTxt) {
        btnExportTxt.addEventListener("click", () => {
            const text = getCleanScriptTextFromDOM();
            const baseName = (scriptFilename.textContent || "script").replace(/[^a-zA-Z0-9_-]/g, "_").toLowerCase();
            downloadFile(`${baseName}_CLEARED.txt`, text, "text/plain");
            addFeedLog(`Exported clean screenplay: ${baseName}_CLEARED.txt`);
        });
    }

    if (btnExportFdx) {
        btnExportFdx.addEventListener("click", () => {
            const fdxXml = generateFDXXmlFromDOM();
            const baseName = (scriptFilename.textContent || "script").replace(/[^a-zA-Z0-9_-]/g, "_").toLowerCase();
            downloadFile(`${baseName}_CLEARED.fdx`, fdxXml, "application/xml");
            addFeedLog(`Exported Final Draft XML: ${baseName}_CLEARED.fdx`);
        });
    }

    if (btnExportDocket) {
        btnExportDocket.addEventListener("click", () => {
            if (!currentReport) return;
            const jsonStr = JSON.stringify(currentReport, null, 2);
            const baseName = (scriptFilename.textContent || "script").replace(/[^a-zA-Z0-9_-]/g, "_").toLowerCase();
            downloadFile(`${baseName}_CLEARANCE_DOCKET.json`, jsonStr, "application/json");
            addFeedLog(`Exported legal clearance dossier: ${baseName}_CLEARANCE_DOCKET.json`);
        });
    }

    function downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Extract Clean Text from Screenplay DOM
    function getCleanScriptTextFromDOM() {
        const page = scriptContent.querySelector(".screenplay-page");
        if (!page) return loadedScriptText || scriptContent.innerText;

        let cleanLines = [];
        const blocks = page.querySelectorAll(".script-scene-header, .script-character-cue, .script-parenthetical, .script-dialogue-block, .script-action-line, .script-transition");

        if (blocks.length === 0) {
            let raw = page.innerText;
            raw = raw.replace(/\[EX-\d+:\s*([^\]]+)\]/g, "$1");
            return raw;
        }

        blocks.forEach(b => {
            let text = b.innerText;
            text = text.replace(/\[EX-\d+:\s*([^\]]+)\]/g, "$1").trim();
            if (text) cleanLines.push(text);
        });

        return cleanLines.join("\n\n");
    }

    // Generate Final Draft XML (.fdx)
    function generateFDXXmlFromDOM() {
        const page = scriptContent.querySelector(".screenplay-page");
        let paragraphsXml = "";

        if (page) {
            const elements = page.querySelectorAll("div");
            elements.forEach(el => {
                let type = "Action";
                if (el.classList.contains("script-scene-header")) type = "Scene Heading";
                else if (el.classList.contains("script-character-cue")) type = "Character";
                else if (el.classList.contains("script-parenthetical")) type = "Parenthetical";
                else if (el.classList.contains("script-dialogue-block")) type = "Dialogue";
                else if (el.classList.contains("script-transition")) type = "Transition";
                else if (!el.classList.contains("script-action-line")) return;

                let cleanText = el.innerText.replace(/\[EX-\d+:\s*([^\]]+)\]/g, "$1").trim();
                if (cleanText) {
                    paragraphsXml += `      <Paragraph Type="${type}">\n        <Text>${escapeXml(cleanText)}</Text>\n      </Paragraph>\n`;
                }
            });
        }

        if (!paragraphsXml) {
            paragraphsXml = `      <Paragraph Type="Action">\n        <Text>${escapeXml(getCleanScriptTextFromDOM())}</Text>\n      </Paragraph>\n`;
        }

        return `<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<FinalDraft DocumentType="Script" Template="No" Version="1">
  <Content>
${paragraphsXml}  </Content>
</FinalDraft>`;
    }

    function escapeXml(unsafe) {
        return unsafe.replace(/[<>&'"]/g, (c) => {
            switch (c) {
                case '<': return '&lt;';
                case '>': return '&gt;';
                case '&': return '&amp;';
                case '\'': return '&apos;';
                case '"': return '&quot;';
            }
        });
    }

    // Start Radar Sweep Animation Loop
    function startRadarAnimation() {
        if (!radarCtx) return;
        function animate() {
            sweepAngle = (sweepAngle + 0.035) % (Math.PI * 2);
            drawRadarScope();
            radarAnimFrame = requestAnimationFrame(animate);
        }
        if (radarAnimFrame) cancelAnimationFrame(radarAnimFrame);
        animate();
    }

    // Draw Polar Radar Scope
    function drawRadarScope() {
        if (!radarCtx) return;
        const ctx = radarCtx;
        const w = radarCanvas.width;
        const h = radarCanvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const maxR = cx - 6;

        ctx.clearRect(0, 0, w, h);

        // Background
        ctx.fillStyle = "#04060c";
        ctx.beginPath();
        ctx.arc(cx, cy, maxR, 0, Math.PI * 2);
        ctx.fill();

        // Concentric Range Rings
        const rings = [
            { r: maxR * 0.35, stroke: "rgba(244, 63, 94, 0.25)" },  // Core (Red)
            { r: maxR * 0.68, stroke: "rgba(251, 191, 36, 0.25)" }, // Mid (Amber)
            { r: maxR,        stroke: "rgba(16, 185, 129, 0.3)" }   // Outer (Green)
        ];

        rings.forEach(ring => {
            ctx.strokeStyle = ring.stroke;
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.arc(cx, cy, ring.r, 0, Math.PI * 2);
            ctx.stroke();
        });
        ctx.setLineDash([]);

        // Crosshairs
        ctx.strokeStyle = "rgba(56, 189, 248, 0.18)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cx, cy - maxR);
        ctx.lineTo(cx, cy + maxR);
        ctx.moveTo(cx - maxR, cy);
        ctx.lineTo(cx + maxR, cy);
        ctx.stroke();

        // Animated Sweeping Beam
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(sweepAngle);
        const grad = ctx.createLinearGradient(0, 0, maxR, 0);
        grad.addColorStop(0, "rgba(6, 182, 212, 0.5)");
        grad.addColorStop(1, "rgba(6, 182, 212, 0.0)");

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.arc(0, 0, maxR, -0.35, 0);
        ctx.lineTo(0, 0);
        ctx.fill();

        // Leading Sweep Line
        ctx.strokeStyle = "rgba(56, 189, 248, 0.8)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(maxR, 0);
        ctx.stroke();
        ctx.restore();

        // Draw Element Target Blips
        radarBlips.forEach(b => {
            const bx = cx + Math.cos(b.angle) * b.radius;
            const by = cy + Math.sin(b.angle) * b.radius;

            if (b.stale) {
                ctx.strokeStyle = "#fbbf24";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.arc(bx, by, 5, 0, Math.PI * 2);
                ctx.stroke();
            } else {
                ctx.fillStyle = b.glowColor;
                ctx.beginPath();
                ctx.arc(bx, by, 4.5, 0, Math.PI * 2);
                ctx.fill();

                ctx.fillStyle = b.color;
                ctx.beginPath();
                ctx.arc(bx, by, 2.5, 0, Math.PI * 2);
                ctx.fill();
            }
        });
    }

    // Canvas Click Interaction for Radar Blips
    if (radarCanvas) {
        radarCanvas.addEventListener("click", (e) => {
            const rect = radarCanvas.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;
            const cx = radarCanvas.width / 2;
            const cy = radarCanvas.height / 2;

            for (const b of radarBlips) {
                const bx = cx + Math.cos(b.angle) * b.radius;
                const by = cy + Math.sin(b.angle) * b.radius;
                const dist = Math.hypot(clickX - bx, clickY - by);
                if (dist < 8) {
                    focusElement(b.dept, b.id);
                    break;
                }
            }
        });
    }

    startRadarAnimation();

    // Focus and spotlight an element across UI
    function focusElement(dept, elId) {
        const tabBtn = document.querySelector(`.tab-btn[data-dept="${dept}"]`);
        if (tabBtn) tabBtn.click();

        setTimeout(() => {
            const card = document.getElementById(`card-${elId}`);
            if (card) {
                card.scrollIntoView({ behavior: "smooth", block: "start" });
                card.style.boxShadow = "0 0 24px rgba(56, 189, 248, 0.8)";
                card.style.borderColor = "var(--accent-slate)";
                setTimeout(() => {
                    card.style.boxShadow = "";
                    card.style.borderColor = "";
                }, 1800);
            }
        }, 100);
    }

    // Parse Final Draft (.fdx) XML
    function parseFDXToText(xmlString) {
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlString, "text/xml");
            const paragraphs = xmlDoc.getElementsByTagName("Paragraph");
            let lines = [];
            for (let i = 0; i < paragraphs.length; i++) {
                const p = paragraphs[i];
                const texts = p.getElementsByTagName("Text");
                let lineText = "";
                for (let j = 0; j < texts.length; j++) {
                    lineText += texts[j].textContent;
                }
                lines.push(lineText);
            }
            return lines.join("\n");
        } catch {
            return xmlString;
        }
    }

    // Stage 1: Load Screenplay into Docket without executing API
    function renderUnanalyzedScript(filename, rawText) {
        currentReport = null;
        radarBlips = [];
        scriptFilename.textContent = filename.toUpperCase();
        
        if (scriptStatusDot) scriptStatusDot.className = "status-dot green";

        if (btnRunClearance) {
            btnRunClearance.disabled = false;
            btnRunClearance.innerHTML = '<span class="play-icon">▶</span> Run Clearance';
            btnRunClearance.classList.remove("btn-recheck");
        }

        if (btnExportToggle) btnExportToggle.disabled = false;

        radarStatus.textContent = "STANDBY: SCRIPT LOADED";
        radarStatus.className = "radar-status";

        if (telemetryIntegrity) telemetryIntegrity.textContent = "--%";
        if (telemetryIntegrityBadge) {
            telemetryIntegrityBadge.textContent = "READY";
            telemetryIntegrityBadge.style.color = "var(--accent-cyan)";
            telemetryIntegrityBadge.style.borderColor = "rgba(56, 189, 248, 0.3)";
        }
        metricRed.textContent = "0";
        metricAmber.textContent = "0";
        if (telemetryCorroboration) telemetryCorroboration.textContent = "0%";
        if (telemetryExhibitsCount) telemetryExhibitsCount.textContent = "0 EXHIBITS CITED";

        if (progGreen) progGreen.style.width = "0%";
        if (progAmber) progAmber.style.width = "0%";
        if (progRed) progRed.style.width = "0%";
        if (progLabelGreen) progLabelGreen.textContent = "0% NO ITEMS IDENTIFIED";
        if (progLabelAmber) progLabelAmber.textContent = "0% AMBER REVIEW";
        if (progLabelRed) progLabelRed.textContent = "0% STATUTORY EXPOSURE";

        errorBannerWrapper.style.display = "none";
        errorBannerWrapper.innerHTML = "";

        document.querySelectorAll(".tab-badge").forEach(b => b.textContent = "0");
        monitorCount.textContent = "0 ACTIVE MONITORS";

        const currentYear = new Date().getFullYear();
        const pdCompositionCutoff = currentYear - 96;
        const pdRecordingCutoff = currentYear - 101;

        pluginWorkspace.innerHTML = `
            <div class="preflight-station">
                <div class="cinema-slate preflight-slate">
                    <div class="slate-clapper-stick ready-stick"></div>
                    <div class="slate-board-content">
                        <div class="slate-title-row">
                            <span class="slate-title-text">CLEARFRAME // PRE-FLIGHT CLEARANCE DOCKET</span>
                            <span class="slate-take-badge green">STANDBY // READY FOR SCAN</span>
                        </div>
                        <div class="slate-grid-meta">
                            <div class="slate-meta-field">
                                <span class="field-label">DOCKET FILE:</span>
                                <span class="field-val status-ready">${escapeHtml(filename)}</span>
                            </div>
                            <div class="slate-meta-field">
                                <span class="field-label">ORCHESTRATION:</span>
                                <span class="field-val">Google Cloud Gemini 3.1</span>
                            </div>
                            <div class="slate-meta-field">
                                <span class="field-label">SEARCH REGISTRIES:</span>
                                <span class="field-val">Parallel Web Real-Time</span>
                            </div>
                            <div class="slate-meta-field">
                                <span class="field-label">VERDICT ENGINE:</span>
                                <span class="field-val">Gemini Extraction → Deterministic Rule-ID Mapping</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="preflight-scope-box">
                    <div class="preflight-scope-header">
                        <span>⌖ PRODUCTION CLEARANCE SCOPE (6 SPECIALIZED DEPARTMENTS)</span>
                    </div>
                    <div class="preflight-dept-grid">
                        <div class="preflight-dept-card">
                            <div class="pdept-icon">🎵</div>
                            <div class="pdept-info">
                                <strong>SOUND &amp; MUSIC</strong>
                                <p>Master + sync licenses, composition vs. recording terms, public domain status (compositions through ${pdCompositionCutoff}, recordings through ${pdRecordingCutoff}). Motion picture soundtracks carry film term (17 U.S.C. § 101).</p>
                            </div>
                        </div>
                        <div class="preflight-dept-card">
                            <div class="pdept-icon">📜</div>
                            <div class="pdept-info">
                                <strong>SCRIPT &amp; SIGNAGE</strong>
                                <p>Fictitious 555 numbers, real addresses, business signage, domain names.</p>
                            </div>
                        </div>
                        <div class="preflight-dept-card">
                            <div class="pdept-icon">🎭</div>
                            <div class="pdept-info">
                                <strong>CAST &amp; CHARACTERS</strong>
                                <p>Living person rights of publicity, celebrity personas, trademarked characters.</p>
                            </div>
                        </div>
                        <div class="preflight-dept-card">
                            <div class="pdept-icon">📍</div>
                            <div class="pdept-info">
                                <strong>LOCATIONS &amp; SETS</strong>
                                <p>Private architectural copyright, municipal permits, location release terms.</p>
                            </div>
                        </div>
                        <div class="preflight-dept-card">
                            <div class="pdept-icon">🏷️</div>
                            <div class="pdept-info">
                                <strong>PROPS &amp; BRANDS</strong>
                                <p>Lanham Act trade dress, consumer brands, false endorsement liabilities.</p>
                            </div>
                        </div>
                        <div class="preflight-dept-card">
                            <div class="pdept-icon">🎨</div>
                            <div class="pdept-info">
                                <strong>CAMERA &amp; VISUALS</strong>
                                <p>Artwork provenance, VARA visual artists rights, museum &amp; gallery copyright.</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="preflight-action-callout">
                    <div class="callout-icon">⚡</div>
                    <div class="callout-text">
                        <strong>DOCKET ARMED &amp; READY</strong>
                        <p>Click the green <strong>▶ Run Clearance</strong> button in the docket header to execute Google Cloud Gemini &amp; Parallel legal verification.</p>
                    </div>
                </div>
            </div>`;

        // Render formatted screenplay lines
        const rawLines = rawText.split("\n");
        let isDialogue = false;
        let html = `<div class="screenplay-page ${isEditMode ? 'edit-mode' : ''}" contenteditable="${isEditMode ? 'true' : 'false'}" spellcheck="false"><div class="script-scene-block">`;

        rawLines.forEach(line => {
            const trimmed = line.trim();
            if (!trimmed) {
                isDialogue = false;
                return;
            }

            if (/^(INT\.|EXT\.|SCENE)/i.test(trimmed)) {
                html += `<div class="script-scene-header">${escapeHtml(trimmed)}</div>`;
                isDialogue = false;
            } else if (/^(CUT TO:|FADE OUT|FADE IN:|DISSOLVE TO:)/i.test(trimmed)) {
                html += `<div class="script-transition">${escapeHtml(trimmed)}</div>`;
                isDialogue = false;
            } else if (trimmed === trimmed.toUpperCase() && trimmed.length < 35 && !trimmed.endsWith(".")) {
                html += `<div class="script-character-cue">${escapeHtml(trimmed)}</div>`;
                isDialogue = true;
            } else if (trimmed.startsWith("(") && trimmed.endsWith(")")) {
                html += `<div class="script-parenthetical">${escapeHtml(trimmed)}</div>`;
            } else if (isDialogue) {
                html += `<div class="script-dialogue-block">${escapeHtml(trimmed)}</div>`;
            } else {
                html += `<div class="script-action-line">${escapeHtml(trimmed)}</div>`;
            }
        });

        html += `</div></div>`;
        scriptContent.innerHTML = html;

        attachEditorListeners();
        addFeedLog(`Mounted screenplay docket: ${filename}. Click ▶ Run Clearance to analyze.`);
    }

    // Attach Inline Editing & Autosave Listener
    function attachEditorListeners() {
        const page = scriptContent.querySelector(".screenplay-page");
        if (!page) return;

        page.addEventListener("input", () => {
            const currentText = getCleanScriptTextFromDOM();
            localStorage.setItem("clearframe_draft_text", currentText);

            if (scriptStatusDot) scriptStatusDot.className = "status-dot amber";

            if (currentReport) {
                if (btnRunClearance) {
                    btnRunClearance.disabled = false;
                    btnRunClearance.innerHTML = '<span class="play-icon">▶</span> Recheck Clearance';
                    btnRunClearance.classList.add("btn-recheck");
                }
                checkStaleFindings(currentText);
            }
        });
    }

    // Traceability: Mark Finding as Stale if user changed the flagged text
    function checkStaleFindings(currentScriptText) {
        if (!currentReport) return;
        const normalizedDoc = currentScriptText.toLowerCase();

        for (const deptKey in currentReport.departments) {
            const summary = currentReport.departments[deptKey];
            summary.elements.forEach(item => {
                const target = item.element.text.toLowerCase();
                const card = document.getElementById(`card-${item.element.id}`);
                const isPresent = normalizedDoc.includes(target);

                if (!isPresent && card) {
                    card.classList.add("stale");
                    if (!card.querySelector(".stale-badge")) {
                        const provBar = card.querySelector(".card-provenance-bar");
                        if (provBar) {
                            const badge = document.createElement("span");
                            badge.className = "stale-badge";
                            badge.innerHTML = "⚠️ SCRIPT EDITED — EVIDENCE STALE";
                            provBar.appendChild(badge);
                        }
                    }
                }

                // Update Radar blip state
                const blip = radarBlips.find(b => b.id === item.element.id);
                if (blip) {
                    blip.stale = !isPresent;
                }
            });
        }
    }

    // Workspace Reset for Scan
    function clearWorkspaceForScan(filename = "script.txt") {
        document.body.classList.add("scanning-active");
        radarBlips = [];
        scriptFilename.textContent = filename.toUpperCase();
        
        radarStatus.textContent = "ANALYZING...";
        radarStatus.className = "radar-status";

        if (telemetryIntegrity) telemetryIntegrity.textContent = "--%";
        if (telemetryIntegrityBadge) {
            telemetryIntegrityBadge.textContent = "ANALYZING";
            telemetryIntegrityBadge.style.color = "var(--accent-cyan)";
        }
        metricRed.textContent = "0";
        metricAmber.textContent = "0";
        if (telemetryCorroboration) telemetryCorroboration.textContent = "--%";
        if (telemetryExhibitsCount) telemetryExhibitsCount.textContent = "0 EXHIBITS CITED";

        errorBannerWrapper.style.display = "none";
        errorBannerWrapper.innerHTML = "";

        if (loadingStepTimer) clearInterval(loadingStepTimer);

        pluginWorkspace.innerHTML = `
            <div class="forensic-scanner-loading">
                <div class="cinema-slate">
                    <div class="slate-clapper-stick"></div>
                    <div class="slate-board-content">
                        <div class="slate-title-row">
                            <span class="slate-title-text">CLEARFRAME // PRODUCTION FORENSIC SCAN</span>
                            <span class="slate-take-badge">TAKE 01</span>
                        </div>
                        <div class="slate-grid-meta">
                            <div class="slate-meta-field">
                                <span class="field-label">DOCKET FILE:</span>
                                <span class="field-val">${escapeHtml(filename)}</span>
                            </div>
                            <div class="slate-meta-field">
                                <span class="field-label">AI ORCHESTRATION:</span>
                                <span class="field-val">Google Cloud Gemini 3.1</span>
                            </div>
                            <div class="slate-meta-field">
                                <span class="field-label">REGISTRY CITATIONS:</span>
                                <span class="field-val">Parallel Web Live</span>
                            </div>
                            <div class="slate-meta-field">
                                <span class="field-label">VERDICT ENGINE:</span>
                                <span class="field-val">Gemini Extraction → Deterministic Rule-ID Mapping</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="scanline-progress-wrapper">
                    <div class="scanline-laser"></div>
                </div>

                <div class="pipeline-step-ticker">
                    <div class="pipeline-step-row active" id="pstep-0">
                        <span class="step-marker"></span> [ 01 ] Ingesting production screenplay &amp; scene sluglines...
                    </div>
                    <div class="pipeline-step-row" id="pstep-1">
                        <span class="step-marker"></span> [ 02 ] Extracting 6-department clearance entities (Gemini 3.1)...
                    </div>
                    <div class="pipeline-step-row" id="pstep-2">
                        <span class="step-marker"></span> [ 03 ] Cross-referencing Parallel legal registries &amp; case basis...
                    </div>
                    <div class="pipeline-step-row" id="pstep-3">
                        <span class="step-marker"></span> [ 04 ] Computing statutory risk ratings &amp; rule assignments...
                    </div>
                    <div class="pipeline-step-row" id="pstep-4">
                        <span class="step-marker"></span> [ 05 ] Registering standing Parallel live watchdog listeners...
                    </div>
                </div>
            </div>`;

        let currentPStep = 0;
        loadingStepTimer = setInterval(() => {
            if (currentPStep < 4) {
                const prev = document.getElementById(`pstep-${currentPStep}`);
                if (prev) {
                    prev.className = "pipeline-step-row completed";
                }
                currentPStep++;
                const next = document.getElementById(`pstep-${currentPStep}`);
                if (next) {
                    next.className = "pipeline-step-row active";
                }
            }
        }, 3000);

        addFeedLog(`Executing clearance analysis pipeline for ${escapeHtml(filename)}...`);
    }

    // Parse Raw Error
    function parseErrorMessage(rawError) {
        if (!rawError) return { title: "Clearance Pipeline Error", summary: "An unexpected error occurred during execution." };
        const str = typeof rawError === "string" ? rawError : JSON.stringify(rawError);

        if (str.includes("429") || str.includes("RESOURCE_EXHAUSTED")) {
            const retryMatch = str.match(/retry in\s+([0-9.]+\s*s|[0-9.]+\s*seconds)/i);
            const retryStr = retryMatch ? ` Please retry in ${retryMatch[1]}.` : "";
            return {
                title: "Gemini API Quota Exhausted (429)",
                summary: `The request rate limit for the configured Gemini model was exceeded.${retryStr}`
            };
        }

        if (str.includes("503") || str.includes("UNAVAILABLE")) {
            return {
                title: "Google AI Service Temporarily Unavailable (503)",
                summary: "Gemini model is currently experiencing high demand. Please retry shortly."
            };
        }

        if (str.includes("PARALLEL_API_KEY")) {
            return {
                title: "Parallel API Credential Error",
                summary: "PARALLEL_API_KEY is not configured or is invalid. Set a valid API key in .env."
            };
        }

        return {
            title: "Pipeline Execution Error",
            summary: str.length > 180 ? str.slice(0, 180) + "..." : str
        };
    }

    // Show Error Banner
    function showErrorBanner(filename, hash, errorMsg) {
        document.body.classList.remove("scanning-active");
        if (loadingStepTimer) clearInterval(loadingStepTimer);
        currentReport = null;
        radarBlips = [];
        const parsed = parseErrorMessage(errorMsg);

        scriptFilename.textContent = (filename || "script.txt").toUpperCase();
        if (scriptStatusDot) scriptStatusDot.className = "status-dot amber";

        scriptContent.innerHTML = `
            <div class="empty-state error">
                <p style="color: var(--risk-red); font-weight: 700; font-size: 14px; font-family: var(--font-mono);">❌ DOCKET SCAN HALTED</p>
                <p style="font-size: 12px; color: var(--text-dim); margin-top: 6px;">Zero fallback or synthetic data emitted. Fix underlying credential/service failure.</p>
            </div>`;

        radarStatus.textContent = "HALTED";
        radarStatus.className = "radar-status error";

        errorBannerWrapper.style.display = "block";
        errorBannerWrapper.innerHTML = `
            <div class="error-banner">
                <h4>⚠️ ${escapeHtml(parsed.title)}</h4>
                <p style="margin-bottom: 6px;">${escapeHtml(parsed.summary)}</p>
                <div style="font-family: var(--font-mono); font-size: 10px; opacity: 0.85; margin-bottom: 6px;">
                    <span>TARGET: <strong>${escapeHtml(filename)}</strong></span> | 
                    <span>HASH: <strong>${escapeHtml(hash || "N/A")}</strong></span>
                </div>
                <details class="error-trace-details">
                    <summary style="cursor: pointer; font-size: 10px; font-family: var(--font-mono); color: var(--accent-slate);">
                        🔍 Click to view technical error payload
                    </summary>
                    <div class="error-details" style="margin-top: 6px;">${escapeHtml(errorMsg)}</div>
                </details>
            </div>`;

        pluginWorkspace.innerHTML = `
            <div class="empty-state">
                <p style="color: var(--risk-red);">❌ Clearance docket halted. Check service logs and re-execute scan.</p>
            </div>`;

        addFeedLog(`🚨 PIPELINE ERROR: ${parsed.title} — ${parsed.summary}`);
    }

    // Run Demo Scan
    btnDemo.addEventListener("click", async () => {
        const fixture = demoFixtureSelect ? demoFixtureSelect.value : "scene_01";
        const fnameMap = {
            "scene_01": "scene_01.txt",
            "scene_02": "scene_02.txt",
            "gauntlet": "gauntlet_script.txt"
        };
        const fname = fnameMap[fixture] || `${fixture}.txt`;

        clearWorkspaceForScan(fname);
        btnDemo.disabled = true;
        if (btnRunClearance) btnRunClearance.disabled = true;

        try {
            const res = await fetch(`/api/clearance/demo/${fixture}`);
            const data = await res.json();

            if (!res.ok || data.status === "INCOMPLETE_ERROR") {
                const errMsg = data.detail || "Demo execution failed.";
                showErrorBanner(data.filename || fname, data.script_hash || "", errMsg);
                return;
            }

            currentReport = data;
            renderReport(currentReport);
            addFeedLog(`Clearance scan synthesized for ${data.title || fname}. Live Parallel Monitors registered.`);
        } catch (err) {
            showErrorBanner(fname, "", err.message);
        } finally {
            btnDemo.disabled = false;
            if (btnRunClearance) btnRunClearance.disabled = false;
        }
    });

    // Stage 1 File Selection: Read & Display File in Docket without triggering API
    scriptFileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;

        loadedFile = file;
        const reader = new FileReader();
        reader.onload = (event) => {
            const raw = event.target.result;
            if (file.name.toLowerCase().endsWith(".fdx")) {
                loadedScriptText = parseFDXToText(raw);
            } else {
                loadedScriptText = raw;
            }
            renderUnanalyzedScript(file.name, loadedScriptText);
        };
        reader.readAsText(file);
    });

    // Stage 2: Execute Clearance on Loaded or Edited Script
    if (btnRunClearance) {
        btnRunClearance.addEventListener("click", async () => {
            const latestScriptText = getCleanScriptTextFromDOM();
            if (!latestScriptText.trim()) {
                scriptFileInput.click();
                return;
            }

            let rawFname = (scriptFilename.textContent || (loadedFile ? loadedFile.name : "script.txt")).trim();
            while (rawFname.toLowerCase().endsWith(".txt.txt")) {
                rawFname = rawFname.slice(0, -4);
            }
            while (rawFname.toLowerCase().endsWith(".fdx.fdx")) {
                rawFname = rawFname.slice(0, -4);
            }
            let fname = rawFname;
            if (!fname.toLowerCase().endsWith(".txt") && !fname.toLowerCase().endsWith(".fdx")) {
                fname = `${fname}.txt`;
            }

            clearWorkspaceForScan(fname);
            btnRunClearance.disabled = true;
            btnDemo.disabled = true;

            const formData = new FormData();
            const blob = new Blob([latestScriptText], { type: "text/plain" });
            formData.append("file", blob, fname);
            formData.append("filename", fname);

            try {
                const res = await fetch("/api/clearance/analyze", {
                    method: "POST",
                    body: formData
                });

                const data = await res.json();

                if (!res.ok || data.status === "INCOMPLETE_ERROR") {
                    const errMsg = data.detail || "Script analysis failed.";
                    showErrorBanner(data.filename || fname, data.script_hash || "", errMsg);
                    return;
                }

                currentReport = data;
                renderReport(currentReport);
                addFeedLog(`Production clearance analysis complete for ${fname}`);
            } catch (err) {
                showErrorBanner(fname, "", err.message);
            } finally {
                btnRunClearance.disabled = false;
                btnDemo.disabled = false;
            }
        });
    }

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
        document.body.classList.remove("scanning-active");
        if (loadingStepTimer) clearInterval(loadingStepTimer);
        scriptFilename.textContent = (report.filename || report.title || "DOCKET").toUpperCase();
        if (scriptStatusDot) scriptStatusDot.className = "status-dot green";

        if (btnRunClearance) {
            btnRunClearance.innerHTML = '<span class="play-icon">▶</span> Run Clearance';
            btnRunClearance.classList.remove("btn-recheck");
            btnRunClearance.disabled = false;
        }

        if (btnExportToggle) btnExportToggle.disabled = false;

        radarStatus.textContent = report.status === "COMPLETE" ? "ONLINE" : "INCOMPLETE";
        radarStatus.className = report.status === "COMPLETE" ? "radar-status" : "radar-status error";

        const total = report.total_elements || 0;
        metricRed.textContent = report.red_count;
        metricAmber.textContent = report.amber_count;

        // Calculate Title Integrity Index (Weighted Clearance Score)
        if (total > 0) {
            const integrityScore = Math.round(((report.green_count * 1.0 + report.amber_count * 0.45) / total) * 100);
            if (telemetryIntegrity) telemetryIntegrity.textContent = `${integrityScore}%`;
            if (telemetryIntegrityBadge) {
                if (integrityScore >= 75) {
                    telemetryIntegrityBadge.textContent = "PASS / CLEAR";
                    telemetryIntegrityBadge.style.color = "var(--risk-green)";
                    telemetryIntegrityBadge.style.borderColor = "var(--risk-green-border)";
                } else if (integrityScore >= 45) {
                    telemetryIntegrityBadge.textContent = "REVIEW REQ";
                    telemetryIntegrityBadge.style.color = "var(--risk-amber)";
                    telemetryIntegrityBadge.style.borderColor = "var(--risk-amber-border)";
                } else {
                    telemetryIntegrityBadge.textContent = "ACTION REQ";
                    telemetryIntegrityBadge.style.color = "var(--risk-red)";
                    telemetryIntegrityBadge.style.borderColor = "var(--risk-red-border)";
                }
            }

            // Progress bar
            const greenPct = Math.round((report.green_count / total) * 100);
            const amberPct = Math.round((report.amber_count / total) * 100);
            const redPct = Math.max(0, 100 - greenPct - amberPct);

            if (progGreen) progGreen.style.width = `${greenPct}%`;
            if (progAmber) progAmber.style.width = `${amberPct}%`;
            if (progRed) progRed.style.width = `${redPct}%`;

            if (progLabelGreen) progLabelGreen.textContent = `${greenPct}% NO ACTION REQUIRED (${report.green_count})`;
            if (progLabelAmber) progLabelAmber.textContent = `${amberPct}% AMBER REVIEW (${report.amber_count})`;
            if (progLabelRed) progLabelRed.textContent = `${redPct}% STATUTORY EXPOSURE (${report.red_count})`;
        }

        // Count basis exhibits & corroboration
        let totalBasisExhibits = 0;
        let activeMonitors = 0;
        const allElementsList = [];

        for (const [deptKey, summary] of Object.entries(report.departments)) {
            const badge = document.getElementById(`badge-${deptKey}`);
            if (badge) badge.textContent = summary.total_elements;
            activeMonitors += (summary.red_count + summary.amber_count);

            summary.elements.forEach(item => {
                allElementsList.push(item);
                if (item.finding && item.finding.basis && item.finding.basis.length > 0) {
                    totalBasisExhibits += item.finding.basis.length;
                }
            });
        }

        const totalResolved = (report.green_count || 0) + (report.red_count || 0);
        const resolvedPct = total > 0 ? Math.round((totalResolved / total) * 100) : 0;

        if (telemetryCorroboration) telemetryCorroboration.textContent = `${resolvedPct}%`;
        if (telemetryExhibitsCount) telemetryExhibitsCount.textContent = `${totalBasisExhibits} EXHIBITS CITED`;
        monitorCount.textContent = `${activeMonitors} ACTIVE MONITORS`;

        // Populate Radar Blips for Polar Canvas
        radarBlips = [];
        const maxR = (radarCanvas ? radarCanvas.width / 2 : 70) - 8;
        const totalItems = allElementsList.length;

        allElementsList.forEach((item, idx) => {
            const angle = (idx / Math.max(1, totalItems)) * Math.PI * 2;
            const rating = item.verdict.rating.toLowerCase();
            let radius = maxR * 0.85;
            let color = "#10b981";
            let glowColor = "rgba(16, 185, 129, 0.4)";

            if (rating === "red") {
                radius = maxR * 0.28 + (idx % 3) * 3;
                color = "#f43f5e";
                glowColor = "rgba(244, 63, 94, 0.6)";
            } else if (rating === "amber") {
                radius = maxR * 0.58 + (idx % 3) * 3;
                color = "#fbbf24";
                glowColor = "rgba(251, 191, 36, 0.5)";
            }

            radarBlips.push({
                angle: angle,
                radius: radius,
                color: color,
                glowColor: glowColor,
                id: item.element.id,
                dept: item.element.department,
                text: item.element.text,
                stale: false
            });
        });

        // Render Script Text & Active Department Cards
        renderScriptText(report);
        renderDepartmentCards();
    }

    function renderScriptText(report) {
        if (!report.scenes || report.scenes.length === 0) return;

        const elementHighlights = [];
        let exhibitCounter = 1;
        for (const deptKey in report.departments) {
            const summary = report.departments[deptKey];
            summary.elements.forEach(item => {
                elementHighlights.push({
                    text: item.element.text,
                    id: item.element.id,
                    dept: item.element.department,
                    rating: item.verdict.rating.toLowerCase(),
                    ruleId: item.verdict.rule_id,
                    exhibitNo: String(exhibitCounter++).padStart(2, "0")
                });
            });
        }

        let html = `<div class="screenplay-page ${isEditMode ? 'edit-mode' : ''}" contenteditable="${isEditMode ? 'true' : 'false'}" spellcheck="false">`;

        report.scenes.forEach(scene => {
            html += `<div class="script-scene-block">`;
            html += `<div class="script-scene-header">${escapeHtml(scene.heading)}</div>`;

            const rawLines = scene.text.split("\n");
            let isDialogue = false;

            rawLines.forEach(line => {
                const trimmed = line.trim();
                if (!trimmed) {
                    isDialogue = false;
                    return;
                }

                if (/^(INT\.|EXT\.|SCENE)/i.test(trimmed)) {
                    html += `<div class="script-scene-header">${highlightText(trimmed, elementHighlights)}</div>`;
                    isDialogue = false;
                } else if (/^(CUT TO:|FADE OUT|FADE IN:|DISSOLVE TO:)/i.test(trimmed)) {
                    html += `<div class="script-transition">${highlightText(trimmed, elementHighlights)}</div>`;
                    isDialogue = false;
                } else if (trimmed === trimmed.toUpperCase() && trimmed.length < 35 && !trimmed.endsWith(".")) {
                    html += `<div class="script-character-cue">${highlightText(trimmed, elementHighlights)}</div>`;
                    isDialogue = true;
                } else if (trimmed.startsWith("(") && trimmed.endsWith(")")) {
                    html += `<div class="script-parenthetical">${highlightText(trimmed, elementHighlights)}</div>`;
                } else if (isDialogue) {
                    html += `<div class="script-dialogue-block">${highlightText(trimmed, elementHighlights)}</div>`;
                } else {
                    html += `<div class="script-action-line">${highlightText(trimmed, elementHighlights)}</div>`;
                }
            });

            html += `</div>`;
        });

        html += `</div>`;
        scriptContent.innerHTML = html;

        // Click handlers on inline highlights (when in Read mode)
        scriptContent.querySelectorAll(".hl-risk").forEach(pill => {
            pill.addEventListener("click", (e) => {
                if (isEditMode) return;
                const dept = pill.dataset.dept;
                const elId = pill.dataset.elId;
                focusElement(dept, elId);
            });
        });

        attachEditorListeners();
    }

    function highlightText(text, elements) {
        let escaped = escapeHtml(text);
        elements.forEach(item => {
            const escapedTarget = escapeHtml(item.text);
            if (escaped.includes(escapedTarget)) {
                const ruleTag = (!item.ruleId || item.ruleId === "DEFAULT-000") ? "UNCLASSIFIED" : item.ruleId;
                const pillHtml = `<span class="hl-risk ${item.rating}" contenteditable="false" data-el-id="${item.id}" data-dept="${item.dept}" title="[EX-${item.exhibitNo}] ${item.rating.toUpperCase()} [${ruleTag}] — Click to inspect exhibit">[EX-${item.exhibitNo}: ${escapedTarget}]</span>`;
                escaped = escaped.split(escapedTarget).join(pillHtml);
            }
        });
        return escaped;
    }

    function renderDepartmentCards() {
        if (!currentReport) return;
        const summary = currentReport.departments[activeDepartment];

        if (!summary || !summary.elements || summary.elements.length === 0) {
            pluginWorkspace.innerHTML = `<div class="empty-state"><p>No flagged clearance liabilities recorded in this department.</p></div>`;
            return;
        }

        let html = "";
        summary.elements.forEach(item => {
            const el = item.element;
            const verdict = item.verdict;
            const finding = item.finding;
            const ratingClass = verdict.rating.toLowerCase();
            const ruleDisplay = (!verdict.rule_id || verdict.rule_id === "DEFAULT-000") 
                ? "UNCLASSIFIED — NO RULE MATCH" 
                : `[${verdict.rule_id}]`;

            html += `
            <div class="clearance-card ${ratingClass}" id="card-${el.id}">
                <div class="card-provenance-bar">
                    <span>📑 EXHIBIT // <strong>${escapeHtml(el.id)}</strong></span>
                    <span>SOURCE: <strong>${escapeHtml(currentReport.filename)}</strong></span>
                </div>

                <div class="card-header">
                    <div class="card-title-group">
                        <h4>${escapeHtml(el.text)}</h4>
                        <span class="card-subtype">${escapeHtml(el.subtype)}</span>
                    </div>
                    <div class="verdict-pill ${ratingClass}">
                        ${verdict.rating} <span class="rule-id">${ruleDisplay}</span>
                    </div>
                </div>

                <div class="context-quote">"${escapeHtml(el.quoted_source_passage || el.context_snippet)}"</div>

                <div class="rationale-box">
                    <strong>CLEARANCE ASSESSMENT:</strong> ${escapeHtml(verdict.rationale)}
                </div>

                ${renderBasisSection(finding)}
            </div>`;
        });

        pluginWorkspace.innerHTML = html;
    }

    function cleanMarkdownReasoning(reasoning) {
        if (!reasoning) return "";
        let text = reasoning;
        try {
            const parser = new DOMParser();
            const doc = parser.parseFromString(reasoning, "text/html");
            text = doc.body.textContent || reasoning;
        } catch {
            text = reasoning;
        }

        text = text.replace(/^#+\s+/gm, "");
        text = text.replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1");
        text = text.replace(/(\*\*|__)(.*?)\1/g, "$2");
        text = text.replace(/(\*|_)(.*?)\1/g, "$2");
        text = text.replace(/`([^`]+)`/g, "$1");
        text = text.replace(/^\*\s+/gm, "• ");
        text = text.replace(/<[^>]+>/g, "");
        return text.trim();
    }

    function extractDomain(url) {
        try {
            const parsed = new URL(url);
            return parsed.hostname.replace(/^www\./, "");
        } catch {
            return "source";
        }
    }

    function renderBasisSection(finding) {
        if (!finding || !finding.basis || finding.basis.length === 0) {
            return `<div class="basis-section"><div class="basis-header"><span>PARALLEL EVIDENTIARY BASIS</span></div><div class="basis-item"><div class="basis-reasoning">Deterministic statutory / regulatory determination. No live search anomaly detected.</div></div></div>`;
        }

        let basisHtml = "";
        finding.basis.forEach(b => {
            const confTag = b.confidence !== null && b.confidence !== undefined 
                ? `<span class="confidence-tag">CONF: ${Math.round(b.confidence * 100)}%</span>` 
                : "";

            const cleanedReasoning = cleanMarkdownReasoning(b.reasoning);
            const domain = extractDomain(b.url);

            basisHtml += `
            <div class="basis-item">
                <div class="basis-reasoning">${escapeHtml(cleanedReasoning)}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                    <a href="${b.url}" target="_blank" rel="noopener" class="basis-citation-chip">🔗 [DOC-REF: ${escapeHtml(domain)}]</a>
                    ${confTag}
                </div>
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
