// Narrated product demo: one entry per scene. Narration explains features and caveats; it never reads
// out live figures, so the script itself contains no agency data.
// beat.target: CSS selector, "card:<h2 text>" (closest card), "text:<visible text>", or "top".
export const SCENES = [
  { kind: 'title', title: 'Agency Intelligence', sub: 'A read-only performance dashboard for OnlyFans agencies, built on the Infloww API',
    say: 'This is Agency Intelligence: a read-only dashboard that turns your Infloww data into one clear view of revenue, creators, chatters, fans and marketing.' },

  { path: '/', beats: [
    { target: 'top', caption: 'Global filters: date range, creators, gross or net' },
    { target: '[data-testid="hero-revenue"]', caption: 'Revenue for the period, compared with the previous period' },
    { target: 'text:Top creator', caption: 'Top creator spotlight' },
  ], say: 'Every page shares the same filters at the top: the date range, which creators to include, and whether money is shown gross or net of OnlyFans fees. The overview opens with revenue for the period and how it compares with the previous period of the same length, next to a spotlight on your top earning creator.' },

  { path: '/', beats: [
    { target: 'text:Net revenue', caption: 'Net = gross minus the OnlyFans platform fee' },
    { target: 'text:Chatter-attributed sales', caption: 'Sales Infloww credits to a chatter' },
    { target: 'card:Revenue performance', caption: 'Daily revenue trend' },
  ], say: 'The key numbers sit in cards with small trend lines. Net revenue is gross minus the platform fee, which is not the same as agency profit. Chatter attributed sales are exactly what Infloww credits to a chatter, using your own Infloww sales settings, so creator revenue is never assigned to chatters by guesswork.' },

  { path: '/', beats: [
    { target: 'card:Revenue by source', caption: 'Subscriptions, messages, posts and tips' },
    { target: 'card:Attribution coverage', caption: 'How much revenue has a chatter attached' },
    { target: 'card:Subscriber growth', caption: 'New subscribers from creator reports' },
  ], say: 'Further down, revenue is split by source. The attribution gauge shows what share of revenue Infloww links to a chatter, so you can see how far the chatter numbers can be trusted. Subscriber growth comes straight from the creator reports.' },

  { path: '/creators', beats: [
    { target: 'card:Creator directory', caption: 'Every connected creator, sortable and searchable' },
    { target: 'card:Revenue leaderboard', caption: 'Ranked by revenue in the selected range' },
  ], say: 'The creators page lists every connected account with revenue, growth and audience health. Click any row to open the full creator profile.' },

  { path: '__TOP_CREATOR__', beats: [
    { target: 'top', caption: 'Creator profile' },
    { target: 'card:Revenue breakdown', caption: 'Where this creator earns' },
    { target: 'card:Top spenders', caption: 'Fans are pseudonymised' },
  ], say: 'A creator profile shows revenue history, the revenue mix, engagement and subscriber retention. Top spenders are shown with pseudonymised names, so fan identities are protected even inside the agency.' },

  { path: '/chatters', beats: [
    { target: 'card:Chatter leaderboard', caption: 'Attributed sales per chatter' },
    { target: 'card:How sales were attributed', caption: 'The attribution rule behind every number' },
    { target: 'card:Creator × chatter matrix', caption: 'Who sells best on which creator' },
  ], say: 'The chatters page ranks your team by attributed sales and shows the rule Infloww used to attribute them. The matrix shows which chatter performs best on which creator. Shift hours and wages are not in the Infloww API, so the dashboard says so instead of inventing them.' },

  { path: '/fans', beats: [
    { target: 'card:Subscriber trend', caption: 'Active and expired fans over time' },
    { target: 'card:Fan segments', caption: 'VIP, high value, regular, non-spender' },
    { target: 'card:Spending distribution', caption: 'How spend is spread across paying fans' },
  ], say: 'Fan intelligence tracks active and expired subscribers, and groups paying fans into segments such as VIP and at risk. The thresholds are transparent rules you can change in settings.' },

  { path: '/revenue', beats: [
    { target: 'card:Revenue by source over time', caption: 'Revenue mix over time' },
    { target: 'card:Profit & loss view', caption: 'Reported figures kept apart from estimates' },
    { target: 'card:Infloww invoices', caption: 'Monthly billing from Infloww' },
  ], say: 'Revenue and financials keeps figures reported by Infloww clearly separate from estimates. Commission and payroll estimates only appear once you enter your own rates, because the dashboard never assumes your agency\'s commission.' },

  { path: '/marketing', beats: [
    { target: 'top', caption: 'Link metrics are lifetime totals' },
    { target: 'card:Earnings by traffic source', caption: 'What each traffic source earns' },
    { target: 'card:Campaign leaderboard', caption: 'Add a cost to any link to get ROI' },
  ], say: 'Marketing covers tracking links, free trials and promotions. Infloww reports link metrics as lifetime totals, and the page says so. Enter what a campaign cost, and return on investment is calculated for you.' },

  { path: '/analytics', beats: [
    { target: 'card:Message analytics', caption: 'Mass message reach, conversion and revenue' },
    { target: 'card:Script performance', caption: 'Results per script tag and sequence' },
  ], say: 'Analytics measures mass messages, their reach, conversion and revenue, and how each chat script performs.' },

  { path: '/reports', beats: [
    { target: 'card:Report type', caption: 'Eight ready-made reports' },
    { target: 'card:Daily revenue report', caption: 'Export to CSV, Excel or PDF' },
  ], say: 'Reports turns any view into a CSV, Excel or PDF file, using exactly the same calculations and filters as the dashboard.' },

  { path: '/status', beats: [
    { target: 'card:Data coverage — default window', caption: 'Is every day synced?' },
    { target: 'card:Unsupported / unavailable metrics', caption: 'What the API does not provide' },
  ], say: 'Finally, the status page shows how fresh and complete the data is, the health of every Infloww endpoint, and which metrics the API simply does not provide.' },

  { path: '/', dark: true, beats: [
    { target: 'top', caption: 'Light and dark themes' },
  ], say: 'Everything works in light and dark themes. Times are in UTC, and Infloww data can lag by up to a day.' },

  { kind: 'title', title: 'Read-only by design', sub: 'The API key stays on the server · Nothing in Infloww is ever changed · No mock data',
    say: 'Agency Intelligence is read only. Your Infloww key never leaves the server, nothing in Infloww is ever changed, and every number comes from your real data.' },
]
