/**
 * Contract Intelligence & Risk Scoring AI
 * CUAD 41 NLP Studio Frontend Application
 */

class ContractApp {
    constructor() {
        this.currentDocId = null;
        this.currentAnalysis = null;
        this.cuadSchema = null;
        this.selectedUploadFile = null;
        this.uploadMode = 'file'; // 'file' or 'paste'
        this.activeFilter = 'ALL';
        this.activeCuadFilter = 'ALL';
        
        this.init();
    }

    async init() {
        console.log("Initializing Contract Intelligence Studio...");
        await this.fetchCuadSchema();
        // Automatically load default sample SaaS agreement for instant showcase
        await this.loadSample('saas_master_agreement');
    }

    async fetchCuadSchema() {
        try {
            const res = await fetch('/api/cuad/categories');
            if (res.ok) {
                const data = await res.json();
                this.cuadSchema = data.categories || [];
                this.renderCuadTaxonomyTab();
            }
        } catch (e) {
            console.error("Failed to load CUAD schema:", e);
        }
    }

    async loadSample(sampleId) {
        if (!sampleId) return;
        this.showToast("Analyzing contract with CUAD NLP models...", 2500);
        
        try {
            const res = await fetch(`/api/contracts/samples/${sampleId}`);
            if (!res.ok) throw new Error("Failed to load sample contract");
            const data = await res.json();
            this.handleAnalysisLoaded(data);
            this.showToast(`Analyzed: ${data.filename}`, 3000);
        } catch (e) {
            this.showToast(`Error: ${e.message}`, 4000);
            console.error(e);
        }
    }

    handleAnalysisLoaded(analysisData) {
        this.currentAnalysis = analysisData;
        this.currentDocId = analysisData.doc_id;

        // Enable export button
        const exportBtn = document.getElementById('exportPdfBtn');
        if (exportBtn) exportBtn.disabled = false;

        // Update UI components
        this.renderExecutiveBanner(analysisData);
        this.renderDocumentViewer(analysisData);
        this.renderRiskTab(analysisData);
        this.renderEntitiesTab(analysisData);
        this.renderCuadTaxonomyTab();

        // Update compare doc A field
        const docAInput = document.getElementById('compareDocA');
        if (docAInput) docAInput.value = analysisData.filename;
    }

    renderExecutiveBanner(data) {
        const risk = data.risk_analysis || {};
        const score = risk.composite_score || 0;
        const tier = risk.risk_tier || 'LOW';
        const color = risk.risk_color || '#10B981';

        // Gauge animation
        const gaugeScore = document.getElementById('riskScoreVal');
        const gaugeFill = document.getElementById('gaugeFill');
        const tierBadge = document.getElementById('riskTierBadge');
        const tierDesc = document.getElementById('riskTierDesc');

        if (gaugeScore) gaugeScore.textContent = score;
        if (tierBadge) {
            tierBadge.textContent = `${tier} RISK`;
            tierBadge.style.background = risk.risk_color ? `${color}22` : '';
            tierBadge.style.color = color;
            tierBadge.style.border = `1px solid ${color}`;
        }
        if (tierDesc) tierDesc.textContent = risk.tier_description || '';

        // Calculate stroke-dashoffset (circumference = 2 * PI * 50 ≈ 314.16)
        if (gaugeFill) {
            const offset = 314 - (314 * (score / 100));
            gaugeFill.style.strokeDashoffset = offset;
            gaugeFill.style.stroke = color;
        }

        // Fact Chips
        const parties = data.entities?.parties || [];
        const kpiParties = document.getElementById('kpiParties');
        if (kpiParties) {
            kpiParties.textContent = parties.length > 0 
                ? parties.map(p => p.name).join(' & ') 
                : 'Preamble Parties';
            kpiParties.title = kpiParties.textContent;
        }

        const kpiJurisdiction = document.getElementById('kpiJurisdiction');
        if (kpiJurisdiction) {
            kpiJurisdiction.textContent = data.entities?.governing_law?.jurisdiction || 'Not Specified';
        }

        const kpiDates = document.getElementById('kpiDates');
        if (kpiDates) {
            const eff = data.entities?.effective_date?.value || 'N/A';
            const exp = data.entities?.expiration_date?.value || 'Evergreen';
            kpiDates.textContent = `${eff} → ${exp}`;
        }

        const kpiAnomalies = document.getElementById('kpiAnomalies');
        if (kpiAnomalies) {
            const catCount = data.category_summary?.total_detected_categories || 0;
            const flagsCount = (risk.anomalies || []).length;
            kpiAnomalies.textContent = `${catCount} CUAD / ${flagsCount} Risk Flags`;
        }

        // Risk Pillars Progress Bars
        const pillars = risk.pillar_breakdown || {};
        this.updatePillarBar('pillar1Score', 'pillar1Bar', pillars.missing_protections?.score || 0, 35, '#F59E0B');
        this.updatePillarBar('pillar2Score', 'pillar2Bar', pillars.unfavorable_terms_and_anomalies?.score || 0, 35, '#EF4444');
        this.updatePillarBar('pillar3Score', 'pillar3Bar', pillars.operational_and_lockin_risk?.score || 0, 20, '#F97316');
        this.updatePillarBar('pillar4Score', 'pillar4Bar', pillars.ambiguity_risk?.score || 0, 10, '#38BDF8');
    }

    updatePillarBar(scoreElemId, barElemId, value, maxVal, color) {
        const scoreElem = document.getElementById(scoreElemId);
        const barElem = document.getElementById(barElemId);
        if (scoreElem) scoreElem.textContent = `${value} / ${maxVal}`;
        if (barElem) {
            const pct = Math.min(100, (value / maxVal) * 100);
            barElem.style.width = `${pct}%`;
            barElem.style.backgroundColor = color;
        }
    }

    renderDocumentViewer(data) {
        const container = document.getElementById('documentContainer');
        const countBadge = document.getElementById('docSegmentCount');
        const titleElem = document.getElementById('docViewTitle');

        if (titleElem) titleElem.textContent = data.filename || 'Contract Document';
        if (countBadge) countBadge.textContent = `${data.total_segments || 0} Clauses`;
        if (!container) return;

        container.innerHTML = '';
        const segments = data.segments || [];

        segments.forEach((seg, index) => {
            const hasAnomaly = (data.risk_analysis?.anomalies || []).some(a => a.segment_id === seg.id);
            const primaryCat = seg.primary_category || 'General';
            const catId = seg.primary_category_id || 'general';

            const card = document.createElement('div');
            card.className = `clause-card ${hasAnomaly ? 'has-risk' : ''}`;
            card.id = `clause-card-${seg.id}`;
            card.dataset.segmentId = seg.id;
            card.dataset.categoryId = catId;
            card.dataset.hasRisk = hasAnomaly;

            card.innerHTML = `
                <div class="clause-card-header">
                    <div class="clause-heading">#${seg.id} ${this.escapeHtml(seg.heading)}</div>
                    <span class="clause-cat-tag">${this.escapeHtml(primaryCat)}</span>
                </div>
                <div class="clause-text">${this.highlightEntitiesInText(seg.text)}</div>
            `;

            card.onclick = () => this.selectClause(seg);
            container.appendChild(card);
        });
    }

    highlightEntitiesInText(text) {
        let escaped = this.escapeHtml(text);
        // Highlight monetary values
        escaped = escaped.replace(/(\$[\d,]+(?:\.\d{2})?(?:\s*(?:USD|million|billion))?)/g, '<span style="color:#38BDF8;font-weight:600;">$1</span>');
        // Highlight notice durations
        escaped = escaped.replace(/(\b\d+\s+(?:days|months|years|hours)\b)/gi, '<span style="color:#F59E0B;font-weight:600;">$1</span>');
        return escaped;
    }

    selectClause(seg) {
        // Remove prior active classes
        document.querySelectorAll('.clause-card').forEach(el => el.classList.remove('active-selected'));
        const selectedCard = document.getElementById(`clause-card-${seg.id}`);
        if (selectedCard) selectedCard.classList.add('active-selected');

        // Populate and open drawer
        const drawer = document.getElementById('clauseDrawer');
        const heading = document.getElementById('drawerHeading');
        const badge = document.getElementById('drawerCategoryBadge');
        const cuadBox = document.getElementById('drawerCuadInfo');
        const riskBox = document.getElementById('drawerRiskInfo');
        const redlineBox = document.getElementById('drawerRedlineBox');
        const rawText = document.getElementById('drawerClauseText');

        if (heading) heading.textContent = seg.heading;
        if (badge) badge.textContent = seg.primary_category || 'Clause Details';
        if (rawText) rawText.textContent = seg.text;

        // CUAD Categories
        const matches = seg.cuad_categories || [];
        if (cuadBox) {
            if (matches.length > 0) {
                cuadBox.innerHTML = matches.map(m => `
                    <div style="margin-bottom: 6px;">
                        <strong>${m.name}</strong> • Confidence: <span style="color:#38BDF8;font-weight:700;">${Math.round(m.confidence * 100)}%</span>
                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top:2px;">${m.mitigation_guidance || ''}</div>
                    </div>
                `).join('');
            } else {
                cuadBox.textContent = "Standard contractual clause (No critical restrictive CUAD category match).";
            }
        }

        // Check if anomaly matches this segment
        const anomaly = (this.currentAnalysis?.risk_analysis?.anomalies || []).find(a => a.segment_id === seg.id);
        if (riskBox) {
            if (anomaly) {
                riskBox.innerHTML = `
                    <div style="color: #EF4444; font-weight: 700; margin-bottom: 4px;">⚠️ ${anomaly.category} (${anomaly.severity})</div>
                    <div>${anomaly.rationale}</div>
                `;
            } else {
                riskBox.innerHTML = `<span style="color: #10B981;">✓ Balanced standard language with no critical anomaly triggers.</span>`;
            }
        }

        if (redlineBox) {
            if (anomaly && anomaly.recommended_redline) {
                redlineBox.innerHTML = `
                    <div style="font-size: 11px; font-weight: 700; color: #10B981; margin-bottom: 4px;">STANDARD REDLINE PROPOSAL:</div>
                    <div>"${anomaly.recommended_redline}"</div>
                    <button class="btn btn-secondary" style="margin-top: 8px; font-size: 11px; padding: 4px 10px;" onclick="window.app.copyRedlineText('${this.escapeQuotes(anomaly.recommended_redline)}')">📋 Copy Redline</button>
                `;
            } else if (matches.length > 0 && matches[0].standard_safe_clause) {
                redlineBox.innerHTML = `
                    <div style="font-size: 11px; font-weight: 700; color: #10B981; margin-bottom: 4px;">BENCHMARK STANDARD PROVISION:</div>
                    <div>"${matches[0].standard_safe_clause}"</div>
                    <button class="btn btn-secondary" style="margin-top: 8px; font-size: 11px; padding: 4px 10px;" onclick="window.app.copyRedlineText('${this.escapeQuotes(matches[0].standard_safe_clause)}')">📋 Copy Clause</button>
                `;
            } else {
                redlineBox.textContent = "No special redline modification required.";
            }
        }

        if (drawer) drawer.style.display = 'flex';
    }

    closeDrawer() {
        const drawer = document.getElementById('clauseDrawer');
        if (drawer) drawer.style.display = 'none';
        document.querySelectorAll('.clause-card').forEach(el => el.classList.remove('active-selected'));
    }

    renderRiskTab(data) {
        const container = document.getElementById('anomaliesList');
        if (!container) return;

        const risk = data.risk_analysis || {};
        const anomalies = risk.anomalies || [];
        const missing = risk.missing_clauses || [];

        if (anomalies.length === 0 && missing.length === 0) {
            container.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 16px; border-radius: 8px; color: #10B981; text-align: center;">
                    ✓ Outstanding compliance profile. No critical high-risk clauses or missing essential covenants detected.
                </div>
            `;
            return;
        }

        let html = '';

        // Render Anomalies
        anomalies.forEach((a, i) => {
            const sevClass = a.severity === 'CRITICAL' ? '' : (a.severity === 'HIGH' ? 'severity-high' : 'severity-medium');
            html += `
                <div class="anomaly-card ${sevClass}">
                    <div class="anomaly-header">
                        <span class="anomaly-title">⚠️ ${this.escapeHtml(a.category)}</span>
                        <span class="badge" style="background:#EF444422; color:#EF4444; border:1px solid #EF4444;">${a.severity} (+${a.points} pts)</span>
                    </div>
                    <div class="anomaly-rationale">${this.escapeHtml(a.rationale)}</div>
                    ${a.flagged_text ? `<div class="anomaly-flagged-text">"${this.escapeHtml(a.flagged_text.substring(0, 240))}..."</div>` : ''}
                    <div class="redline-action-box">
                        <div class="redline-label">Recommended Redline Replacement:</div>
                        <div style="color: var(--text-primary); margin-bottom: 6px;">"${this.escapeHtml(a.recommended_redline)}"</div>
                        <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 8px;" onclick="window.app.copyRedlineText('${this.escapeQuotes(a.recommended_redline)}')">📋 Copy Redline</button>
                    </div>
                </div>
            `;
        });

        // Render Missing Clauses
        missing.forEach(m => {
            html += `
                <div class="anomaly-card severity-medium" style="border-left-color: #F59E0B;">
                    <div class="anomaly-header">
                        <span class="anomaly-title">🛡️ Missing Protection: ${this.escapeHtml(m.item)}</span>
                        <span class="badge" style="background:#F59E0B22; color:#F59E0B; border:1px solid #F59E0B;">MISSING (+${m.impact} pts)</span>
                    </div>
                    <div class="anomaly-rationale">${this.escapeHtml(m.recommendation)}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    renderEntitiesTab(data) {
        const container = document.getElementById('entitiesContainer');
        if (!container) return;

        const ent = data.entities || {};
        const parties = ent.parties || [];
        const values = ent.monetary_values || [];
        const notices = ent.notice_periods || [];
        const payments = ent.payment_terms || [];

        let html = `
            <div class="entity-group">
                <div class="entity-group-title">Contracting Parties & Roles</div>
                <div class="entity-tags-wrap">
                    ${parties.length > 0 ? parties.map(p => `
                        <div class="entity-tag">
                            🏢 <strong>${this.escapeHtml(p.name)}</strong>
                            <span style="color:var(--accent-blue);font-size:11px;">(${this.escapeHtml(p.role || 'Party')})</span>
                        </div>
                    `).join('') : '<div style="color:var(--text-muted);font-size:12px;">No formal corporate entities parsed in header.</div>'}
                </div>
            </div>

            <div class="entity-group">
                <div class="entity-group-title">Key Financial Values & Liability Caps</div>
                <div class="entity-tags-wrap">
                    ${values.length > 0 ? values.map(v => `
                        <div class="entity-tag">
                            💰 <strong>${this.escapeHtml(v.amount)}</strong>
                            <span style="color:var(--text-muted);font-size:11px;">[${this.escapeHtml(v.type)}]</span>
                        </div>
                    `).join('') : '<div style="color:var(--text-muted);font-size:12px;">No distinct monetary amounts identified.</div>'}
                </div>
            </div>

            <div class="entity-group">
                <div class="entity-group-title">Termination & Notice Periods</div>
                <div class="entity-tags-wrap">
                    ${notices.length > 0 ? notices.map(n => `
                        <div class="entity-tag">
                            ⏱️ <strong>${this.escapeHtml(n.duration)}</strong>
                            <span style="color:var(--text-muted);font-size:11px;">(${this.escapeHtml(n.purpose)})</span>
                        </div>
                    `).join('') : '<div style="color:var(--text-muted);font-size:12px;">No fixed notice windows found.</div>'}
                </div>
            </div>

            <div class="entity-group">
                <div class="entity-group-title">Payment & Invoicing Terms</div>
                <div class="entity-tags-wrap">
                    ${payments.length > 0 ? payments.map(pm => `
                        <div class="entity-tag">
                            💳 <strong>${this.escapeHtml(pm)}</strong>
                        </div>
                    `).join('') : '<div style="color:var(--text-muted);font-size:12px;">Standard default payment provisions.</div>'}
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    renderCuadTaxonomyTab() {
        const container = document.getElementById('cuadCategoriesList');
        if (!container || !this.cuadSchema) return;

        const detectedMap = new Map();
        (this.currentAnalysis?.category_summary?.detected_categories || []).forEach(d => {
            detectedMap.set(d.category_id, d);
        });

        let filtered = this.cuadSchema;
        if (this.activeCuadFilter === 'PRESENT') {
            filtered = this.cuadSchema.filter(c => detectedMap.has(c.id));
        } else if (this.activeCuadFilter === 'MISSING') {
            filtered = this.cuadSchema.filter(c => !detectedMap.has(c.id) && c.importance === 'Essential');
        }

        let html = '';
        filtered.forEach(c => {
            const isPresent = detectedMap.has(c.id);
            const detectedInfo = detectedMap.get(c.id);

            html += `
                <div class="cuad-category-item ${isPresent ? 'is-present' : 'is-missing'}">
                    <div>
                        <div style="font-weight: 700; color: var(--text-primary);">
                            ${isPresent ? '✓' : '○'} ${this.escapeHtml(c.name)}
                            <span style="font-size: 10px; font-weight: 600; color: var(--text-muted); margin-left: 6px;">[${c.importance || 'Medium'}]</span>
                        </div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">${this.escapeHtml(c.description)}</div>
                    </div>
                    <div>
                        ${isPresent ? `
                            <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981;">
                                ${detectedInfo.count}x Detected (${Math.round(detectedInfo.highest_confidence * 100)}%)
                            </span>
                        ` : `
                            <span class="badge" style="background: var(--bg-tertiary); color: var(--text-muted);">Not Detected</span>
                        `}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    filterCuadList(mode) {
        this.activeCuadFilter = mode;
        document.querySelectorAll('.cuad-filters-bar .btn-pill').forEach(btn => btn.classList.remove('active'));
        if (event && event.target) event.target.classList.add('active');
        this.renderCuadTaxonomyTab();
    }

    filterHighlights(filterValue) {
        this.activeFilter = filterValue;
        const cards = document.querySelectorAll('.clause-card');

        cards.forEach(card => {
            const catId = card.dataset.categoryId || '';
            const hasRisk = card.dataset.hasRisk === 'true';

            if (filterValue === 'ALL') {
                card.style.display = 'block';
            } else if (filterValue === 'HIGH_RISK') {
                card.style.display = hasRisk ? 'block' : 'none';
            } else if (filterValue === 'liability') {
                card.style.display = (catId.includes('liability') || catId.includes('indemnif')) ? 'block' : 'none';
            } else if (filterValue === 'non_compete') {
                card.style.display = (catId.includes('compete') || catId.includes('solicit')) ? 'block' : 'none';
            } else if (filterValue === 'termination') {
                card.style.display = (catId.includes('terminat') || catId.includes('renewal')) ? 'block' : 'none';
            } else if (filterValue === 'ip') {
                card.style.display = (catId.includes('ip') || catId.includes('license')) ? 'block' : 'none';
            }
        });
    }

    switchTab(tabId) {
        document.querySelectorAll('.tabs-nav .tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

        if (event && event.currentTarget) event.currentTarget.classList.add('active');
        const activePane = document.getElementById(tabId);
        if (activePane) activePane.classList.add('active');
    }

    // Chatbot functionality
    async sendChatMessage(e) {
        if (e) e.preventDefault();
        const input = document.getElementById('chatInput');
        if (!input) return;

        const query = input.value.trim();
        if (!query) return;

        input.value = '';
        this.appendChatBubble('user', query);

        if (!this.currentDocId) {
            this.appendChatBubble('bot', "Please load or upload a contract first so I can analyze it.");
            return;
        }

        try {
            const res = await fetch(`/api/contracts/${this.currentDocId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            if (!res.ok) throw new Error("Q&A service request failed.");
            const data = await res.json();
            this.appendChatBubble('bot', data.answer, data.cited_clause);
        } catch (err) {
            this.appendChatBubble('bot', `Sorry, I encountered an error: ${err.message}`);
        }
    }

    askPresetQuestion(q) {
        const input = document.getElementById('chatInput');
        if (input) input.value = q;
        this.switchTab('chatTab');
        // Activate chat tab button in UI
        const chatNavBtn = document.querySelectorAll('.tabs-nav .tab-btn')[3];
        if (chatNavBtn) {
            document.querySelectorAll('.tabs-nav .tab-btn').forEach(b => b.classList.remove('active'));
            chatNavBtn.classList.add('active');
        }
        this.sendChatMessage();
    }

    appendChatBubble(sender, text, citedClause = null) {
        const container = document.getElementById('chatMessages');
        if (!container) return;

        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${sender}`;

        let citationHtml = '';
        if (citedClause) {
            citationHtml = `
                <div class="cited-clause-card">
                    <strong>📌 Cited Reference: ${this.escapeHtml(citedClause.heading || 'Contract Section')}</strong>
                    <div style="margin-top: 2px;">"${this.escapeHtml(citedClause.text.substring(0, 180))}..."</div>
                </div>
            `;
        }

        bubble.innerHTML = `
            ${sender === 'bot' ? '<div class="bot-avatar">⚖️</div>' : ''}
            <div class="chat-text">
                ${text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}
                ${citationHtml}
            </div>
        `;

        container.appendChild(bubble);
        container.scrollTop = container.scrollHeight;
    }

    // Comparison Mode
    async runComparison() {
        const compareSelect = document.getElementById('compareDocBSelect');
        const container = document.getElementById('compareResultsContainer');
        if (!compareSelect || !container) return;

        const sampleBId = compareSelect.value;
        this.showToast("Computing redline difference & risk shift...", 2000);

        try {
            // Ensure Sample B is loaded
            const sampleBRes = await fetch(`/api/contracts/samples/${sampleBId}`);
            if (!sampleBRes.ok) throw new Error("Could not load comparison contract.");
            const docBData = await sampleBRes.json();

            // Run comparison
            const res = await fetch('/api/contracts/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    doc_id_a: this.currentDocId,
                    doc_id_b: docBData.doc_id
                })
            });

            if (!res.ok) throw new Error("Comparison failed.");
            const diff = await res.json();
            this.renderComparisonResults(diff);
        } catch (e) {
            this.showToast(`Compare Error: ${e.message}`, 4000);
            console.error(e);
        }
    }

    renderComparisonResults(diff) {
        const container = document.getElementById('compareResultsContainer');
        if (!container) return;

        const deltaColor = diff.risk_delta > 0 ? '#EF4444' : (diff.risk_delta < 0 ? '#10B981' : '#38BDF8');

        let html = `
            <div style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div><strong>Risk Score Shift:</strong> ${diff.score_a}/100 (${diff.tier_a}) → <strong>${diff.score_b}/100</strong> (${diff.tier_b})</div>
                    <span class="badge" style="background: ${deltaColor}22; color: ${deltaColor}; border: 1px solid ${deltaColor};">
                        ${diff.risk_delta > 0 ? `+${diff.risk_delta} pts RISK INCREASE` : `${diff.risk_delta} pts RISK DECREASE`}
                    </span>
                </div>
            </div>
        `;

        if (diff.entity_differences && diff.entity_differences.length > 0) {
            html += `<div style="font-weight: 700; font-size: 13px; margin-bottom: 8px;">Key Entity & Term Deviations:</div>`;
            diff.entity_differences.forEach(ed => {
                html += `
                    <div style="background: var(--bg-primary); border-left: 3px solid #F59E0B; padding: 10px; margin-bottom: 8px; border-radius: 4px; font-size: 12.5px;">
                        <strong>${ed.field}:</strong> Contract A: <em>"${ed.contract_a}"</em> → Contract B: <em>"${ed.contract_b}"</em>
                    </div>
                `;
            });
        }

        if (diff.clause_comparisons && diff.clause_comparisons.length > 0) {
            html += `<div style="font-weight: 700; font-size: 13px; margin: 12px 0 8px 0;">Clause Diff Alignment:</div>`;
            diff.clause_comparisons.slice(0, 5).forEach(cc => {
                html += `
                    <div style="background: var(--bg-secondary); border: 1px solid var(--border-color); padding: 10px; border-radius: 6px; margin-bottom: 8px; font-size: 12px;">
                        <div style="display: flex; justify-content: space-between; font-weight: 600; color: var(--accent-blue);">
                            <span>${cc.clause_a.heading}</span>
                            <span>${cc.status} (${Math.round(cc.similarity * 100)}% Match)</span>
                        </div>
                    </div>
                `;
            });
        }

        container.innerHTML = html;
    }

    // Upload Modal Handling
    triggerUploadModal() {
        const modal = document.getElementById('uploadModal');
        if (modal) modal.style.display = 'flex';
    }

    closeUploadModal() {
        const modal = document.getElementById('uploadModal');
        if (modal) modal.style.display = 'none';
        this.selectedUploadFile = null;
        const fileBadge = document.getElementById('selectedFileName');
        if (fileBadge) fileBadge.style.display = 'none';
    }

    switchUploadType(type) {
        this.uploadMode = type;
        const fileSec = document.getElementById('fileUploadSection');
        const pasteSec = document.getElementById('pasteTextSection');
        const tabFile = document.getElementById('modalTabFile');
        const tabPaste = document.getElementById('modalTabPaste');

        if (type === 'file') {
            if (fileSec) fileSec.style.display = 'block';
            if (pasteSec) pasteSec.style.display = 'none';
            if (tabFile) tabFile.classList.add('active');
            if (tabPaste) tabPaste.classList.remove('active');
        } else {
            if (fileSec) fileSec.style.display = 'none';
            if (pasteSec) pasteSec.style.display = 'block';
            if (tabFile) tabFile.classList.remove('active');
            if (tabPaste) tabPaste.classList.add('active');
        }
    }

    handleFileSelected(file) {
        if (!file) return;
        this.selectedUploadFile = file;
        const fileBadge = document.getElementById('selectedFileName');
        if (fileBadge) {
            fileBadge.textContent = `Selected: ${file.name} (${Math.round(file.size / 1024)} KB)`;
            fileBadge.style.display = 'inline-block';
        }
    }

    async submitContractUpload() {
        const formData = new FormData();

        if (this.uploadMode === 'file') {
            if (!this.selectedUploadFile) {
                this.showToast("Please choose a file to upload.", 3000);
                return;
            }
            formData.append('file', this.selectedUploadFile);
        } else {
            const nameInput = document.getElementById('pasteContractName');
            const textInput = document.getElementById('pasteContractText');
            const name = nameInput ? nameInput.value.trim() : 'Custom Agreement';
            const text = textInput ? textInput.value.trim() : '';

            if (!text) {
                this.showToast("Please paste contract text.", 3000);
                return;
            }
            formData.append('raw_text', text);
            formData.append('contract_name', name);
        }

        this.closeUploadModal();
        this.showToast("Parsing document & running NLP risk scoring...", 3000);

        try {
            const res = await fetch('/api/contracts/upload', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error("Upload processing failed");
            const data = await res.json();
            this.handleAnalysisLoaded(data);
            this.showToast(`Analyzed: ${data.filename}`, 3000);
        } catch (e) {
            this.showToast(`Upload Error: ${e.message}`, 4000);
            console.error(e);
        }
    }

    exportReport(type) {
        if (!this.currentDocId) {
            this.showToast("No active document loaded.", 3000);
            return;
        }
        window.open(`/api/contracts/${this.currentDocId}/export/${type}`, '_blank');
    }

    copyRedlineText(text) {
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            this.showToast("Redline language copied to clipboard! 📋", 2000);
        });
    }

    toggleTheme() {
        const body = document.body;
        const icon = document.getElementById('themeIcon');
        if (body.classList.contains('theme-dark')) {
            body.classList.remove('theme-dark');
            body.classList.add('theme-light');
            if (icon) icon.textContent = '🌙';
        } else {
            body.classList.remove('theme-light');
            body.classList.add('theme-dark');
            if (icon) icon.textContent = '☀️';
        }
    }

    showToast(msg, duration = 3000) {
        const toast = document.getElementById('toastNotification');
        if (!toast) return;
        toast.textContent = msg;
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.display = 'none';
        }, duration);
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    escapeQuotes(str) {
        if (!str) return '';
        return String(str).replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, ' ');
    }
}

// Instantiate on load
window.addEventListener('DOMContentLoaded', () => {
    window.app = new ContractApp();
});
