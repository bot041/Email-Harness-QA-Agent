/**
 * Email Harness QA Agent — Frontend Logic
 */

// ── Submit Review ──────────────────────────────────────────────
async function submitReview() {
    const textarea = document.getElementById("emailInput");
    const emailText = textarea.value.trim();

    if (!emailText) {
        showError("Please paste an email before clicking Review.");
        return;
    }

    // Show loading
    hideAll();
    document.getElementById("loadingSection").style.display = "block";
    document.getElementById("reviewBtn").disabled = true;

    try {
        const response = await fetch("/review", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email_text: emailText }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "Server error");
        }

        const data = await response.json();

        // Show results
        hideAll();
        renderResults(data.report);

        // Scroll to results
        document.getElementById("resultsSection").scrollIntoView({ behavior: "smooth" });

    } catch (err) {
        hideAll();
        showError(err.message || "Failed to review email. Please try again.");
    } finally {
        document.getElementById("reviewBtn").disabled = false;
    }
}


// ── Render Results ────────────────────────────────────────────
function renderResults(report) {
    document.getElementById("resultsSection").style.display = "block";

    // Overall Status
    const statusBadge = document.getElementById("statusBadge");
    const statusMessage = document.getElementById("statusMessage");

    let statusClass = "review";
    let statusIcon = "⚠️";

    if (report.overall_status === "Ready to Send") {
        statusClass = "ready";
        statusIcon = "✅";
    } else if (report.overall_status === "Not Ready to Send") {
        statusClass = "not-ready";
        statusIcon = "❌";
    }

    statusBadge.className = `status-badge ${statusClass}`;
    statusBadge.textContent = `${statusIcon} ${report.overall_status}`;
    statusMessage.textContent = report.final_recommendation;

    // Validation Summary
    const summary = report.validation_summary;
    const summaryGrid = document.getElementById("summaryGrid");

    let summaryHTML = `
        <div class="summary-item">
            <div class="count">${summary.total_checks}</div>
            <div class="label">Total Checks</div>
        </div>
        <div class="summary-item">
            <div class="count pass">${summary.passed}</div>
            <div class="label">Passed</div>
        </div>
        <div class="summary-item">
            <div class="count ${summary.issues_found > 0 ? 'fail' : 'pass'}">${summary.issues_found}</div>
            <div class="label">Issues Found</div>
        </div>
    `;

    // Per-validator breakdown
    if (summary.rule_engine_results) {
        summaryHTML += '<div class="summary-item" style="grid-column: 1 / -1;"><hr style="margin: 4px 0 8px;"></div>';
        for (const r of summary.rule_engine_results) {
            summaryHTML += `
                <div class="summary-validator">
                    <span>${r.name}</span>
                    <span class="validator-status ${r.passed ? 'passed' : 'failed'}">${r.passed ? '✓ Passed' : '✗ Issues'}</span>
                </div>
            `;
        }
        summaryHTML += `
            <div class="summary-validator">
                <span>Review</span>
                <span class="validator-status ${summary.deepseek_assessment === 'Ready to Send' ? 'passed' : 'failed'}">
                    ${summary.deepseek_assessment}
                </span>
            </div>
        `;
    }

    summaryGrid.innerHTML = summaryHTML;

    // Issues
    const issuesList = document.getElementById("issuesList");
    if (report.issues.length === 0) {
        issuesList.innerHTML = '<div class="no-issues">🎉 No issues found! Your email looks great.</div>';
        document.getElementById("issuesCard").style.display = "block";
    } else {
        document.getElementById("issuesCard").style.display = "block";
        issuesList.innerHTML = report.issues.map((issue, idx) => `
            <div class="issue-card">
                <div class="issue-header">
                    <span class="issue-title">${idx + 1}. ${escapeHtml(issue.title)}</span>
                </div>
                <div class="issue-description">${escapeHtml(issue.description)}</div>
                ${issue.why_it_matters ? `<div class="issue-why"><strong>Why It Matters</strong>${escapeHtml(issue.why_it_matters)}</div>` : ''}
                ${issue.recommendation ? `<div class="issue-rec"><strong>Recommendation</strong>${escapeHtml(issue.recommendation)}</div>` : ''}
            </div>
        `).join("");
    }

    // AI Review Summary
    if (report.ai_review_summary) {
        document.getElementById("aiReviewCard").style.display = "block";
        document.getElementById("aiReviewText").textContent = report.ai_review_summary;
    } else {
        document.getElementById("aiReviewCard").style.display = "none";
    }

    // Final Recommendation
    document.getElementById("finalRecText").textContent = report.final_recommendation;
}


// ── Load Sample ────────────────────────────────────────────────
let sampleIndex = 0;

const SAMPLES = [
    // Sample 1: Generic subject, missing greeting, typo, duplicate content
    `From: john.anderson@acmecorp.com
To: sarah.chen@clientco.com
Subject: Meeting

Hi,

Just wanted to follow up on our discussion regarding the Q3 deliverables. I think we should definately schedule a meeting to discuss the timeline.

Also, I wanted to follow up on our discussion regarding the Q3 deliverables. I think we should definately schedule a meeting to discuss the timeline.

Let me know what you think.

Best regards,
John Anderson
Senior Project Manager
Acme Corporation`,

    // Sample 2: No subject, no greeting, very short, unclear CTA
    `From: mark.wilson@startup.io
To: hr@globalcorp.com
Subject:

Can you send me the files?

Thanks,
Mark`,

    // Sample 3: ALL CAPS subject, overly casual greeting, no recipient name
    `From: lisa.park@agency.com
To: info@client.org
Subject: URGENT - NEED APPROVAL ASAP - PLEASE RESPOND IMMEDIATELY

Yo,

We need approval on the budget by end of day otherwise the whole project is going to be delayed and we'll miss the deadline which will cause major issues for everyone involved and the client will be really upset about this situation. I've been waiting for two days now and nobody has gotten back to me.

The budget needs approval by end of day today please.

Regards,
Lisa Park`,

    // Sample 4: Many recipients, no greeting, overly long
    `From: david.kim@enterprise.com
To: alice@partner.com, bob@partner.com, carol@partner.com, dan@partner.com, eve@partner.com, frank@partner.com, grace@partner.com, henry@partner.com, iris@partner.com, jane@partner.com, kate@partner.com
Subject:

Please find attached the quarterly report for your review. The report covers all major metrics including revenue growth, customer acquisition costs, churn rates, and expansion revenue from existing accounts across all three regions. I have also included a detailed breakdown of the marketing spend and its attribution to pipeline generation for each quarter.

As discussed in our previous meeting, we need to align on the targets for next quarter and ensure that all teams are working towards the same goals. The executive team will be reviewing these numbers on Friday so please have your feedback ready by Thursday afternoon at the latest.

If you have any questions about specific sections or need clarification on any of the data points mentioned in the report, feel free to reach out to me directly and I will be happy to walk you through the details.

Sincerely,
David Kim
Director of Operations`,

    // Sample 5: Clean, well-written email with minor issues
    `From: emma.richards@consulting.com
To: james.holder@client.com
Subject: Project Update — Website Redesign Milestone 2 Complete

Dear James,

I hope you're having a great week. I'm pleased to share that we've successfully completed Milestone 2 of the website redesign project, on schedule.

Key accomplishments this week:
- Homepage and About page designs finalized and approved
- Mobile responsive layouts tested across all target devices
- Content migration scripts prepared and validated

The next step is to begin Milestone 3, which covers the Services and Contact pages. I've attached the updated timeline for your reference.

Could you please review the milestone summary by Friday and share any feedback? I'm also available for a quick call if you'd prefer to discuss in person.

Best regards,
Emma Richards
Senior Consultant`,

    // Sample 6: Perfect email — should pass with zero issues
    `From: rachel.kim@acmecorp.com
To: david.martinez@partner.com
Subject: Thank You for the Product Demo

Dear David,

Thank you for taking the time to walk us through the product demo yesterday. The team was very impressed with the analytics dashboard and the automated reporting features.

I've shared your pricing sheet with our procurement team, and they will reach out by Wednesday with any follow-up questions.

Looking forward to the next steps.

Best regards,
Rachel Kim
Head of Product
Acme Corporation`,
];

function loadSample() {
    const textarea = document.getElementById("emailInput");
    const btn = document.getElementById("loadSampleBtn");

    textarea.value = SAMPLES[sampleIndex];

    // Cycle to next sample
    sampleIndex = (sampleIndex + 1) % SAMPLES.length;

    // Update button to show which sample is next
    btn.textContent = `📋 Load Sample (${sampleIndex + 1}/${SAMPLES.length})`;
}


// ── Helpers ────────────────────────────────────────────────────
function hideAll() {
    document.getElementById("errorSection").style.display = "none";
    document.getElementById("loadingSection").style.display = "none";
    document.getElementById("resultsSection").style.display = "none";
}

function showError(message) {
    document.getElementById("errorSection").style.display = "block";
    document.getElementById("errorContent").innerHTML = `
        <strong>⚠️ Error</strong>
        <p style="margin-top: 8px;">${escapeHtml(message)}</p>
    `;
    document.getElementById("errorSection").scrollIntoView({ behavior: "smooth" });
}

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ── Keyboard shortcut: Ctrl+Enter to review ───────────────────
document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        submitReview();
    }
});
