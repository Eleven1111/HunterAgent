export const fallbackDashboard = {
  hero: {
    title: "Pilot loop under control.",
    copy: "Mainline workbench and chat share one service layer. Experimental sourcing stays buffered until a human review decision promotes it."
  },
  metrics: [
    { label: "Open jobs", value: "04", foot: "2 new this week" },
    { label: "Drafted submissions", value: "07", foot: "3 awaiting consultant review" },
    { label: "Pending approvals", value: "02", foot: "Formal writes remain gated" },
    { label: "Buffered source items", value: "11", foot: "Feature-flagged review lane" }
  ],
  jobs: [
    { title: "CFO / Northstar Capital", owner: "Pilot Consultant", stage: "Scoring", count: "6 candidates" },
    { title: "VP Finance / Vertex Cloud", owner: "Pilot Owner", stage: "Source review", count: "11 raw items" }
  ],
  approvals: [
    { title: "Submit Lina Chen -> CFO", owner: "Pilot Consultant", status: "Pending" },
    { title: "Export shortlist / Northstar Capital", owner: "Pilot Owner", status: "Pending" }
  ],
  audits: [
    { event: "MATCH_SCORED", resource: "job_order", detail: "CFO shortlist reranked with score.v1" },
    { event: "SUBMISSION_DRAFTED", resource: "submission", detail: "Recommendation draft created for Lina Chen" },
    { event: "SOURCE_ITEM_REVIEWED", resource: "source_item", detail: "Raw lead approved into promote-ready state" }
  ],
  candidates: [
    { name: "Lina Chen", title: "Group CFO", company: "Mercury Pay", city: "Shanghai", source: "Manual upload" },
    { name: "Ivy Song", title: "VP Finance", company: "Atlas Data", city: "Shanghai", source: "Experimental source" }
  ]
};

export const fallbackChatPayload = {
  render_type: "todo_list",
  data: {
    todos: [
      {
        type: "approval",
        title: "submit_recommendation -> submission_demo_01",
        priority: "HIGH",
        link: "/approvals"
      },
      {
        type: "draft",
        title: "Review submission draft submission_demo_02",
        priority: "MEDIUM",
        link: "/submissions"
      }
    ]
  }
};

