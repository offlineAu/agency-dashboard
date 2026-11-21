# API Response Schemas

_Generated from the OpenAPI spec. Amounts are in the smallest currency unit (cents). Times are unix ms unless noted._

## `GET /v1/creators` — Connected creators

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].id` | string | Unique identifier(Creator ID) |
| `.data.list[].name` | string | Creator name |
| `.data.list[].nickName` | string | Nickname |
| `.data.list[].userName` | string | Username |
| `.data.list[].tagName` | string | Tag name |
| `.data.list[].createdTime` | string | Creation time (unix timestamp in milliseconds) |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.platformCode` | string | Platform code |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/all-creators` — All creators

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].id` | string | Unique identifier (Creator ID) |
| `.data.list[].name` | string | Creator name |
| `.data.list[].nickName` | string | Nickname |
| `.data.list[].userName` | string | Username |
| `.data.list[].tagName` | string | Tag name |
| `.data.list[].status` | string | Creator status enum: connected, disconnected, not connect, 2FA, deleted |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].createdTime` | string | Creation time (unix timestamp in milliseconds) |
| `.data.list[].deletedTime` | string | Delete time (unix timestamp in milliseconds) |
| `.data.platformCode` | string | Platform code |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/transactions` — Transactions

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].id` | string | Unique identifier |
| `.data.list[].transactionId` | string | OnlyFans transaction ID |
| `.data.list[].fanId` | string | Fan id |
| `.data.list[].fanName` | string | Fan name |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].createdTime` | string | Creation time (unix timestamp in milliseconds) |
| `.data.list[].tipSource` | string | Tip source enum: Profile, Post, Chat, Stream, Story, Unknown |
| `.data.list[].type` | string | Transaction type enum: Subscription, Recurring Subscription, Tips, Messages, Referrals, Streams, Posts, Unknown |
| `.data.list[].status` | string | Transaction status enum: loading, done, undo, pending_return |
| `.data.list[].amount` | string | Transaction amount (in the smallest unit of the currency) |
| `.data.list[].fee` | string | Fee amount (in the smallest unit of the currency) |
| `.data.list[].net` | string | Net amount (in the smallest unit of the currency) |
| `.data.list[].currency` | string | Currency code |
| `.data.platformCode` | string | Platform code |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/refunds` — Refunds

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].id` | string | Unique identifier |
| `.data.list[].transactionId` | string | OnlyFans transaction ID |
| `.data.list[].fanId` | string | Fan ID |
| `.data.list[].paymentTime` | string | Transaction creation time (unix timestamp in milliseconds) |
| `.data.list[].refundTime` | string | Refund creation time (unix timestamp in milliseconds) |
| `.data.list[].paymentStatus` | string | Refund status enum: undo, loading, done |
| `.data.list[].paymentAmount` | number | Refund amount (in the smallest unit of the currency) |
| `.data.list[].transactionType` | string | Transaction type enum: tips, post, chat_messages, stream, subscribes |
| `.data.list[].currency` | string | Currency code |
| `.data.platformCode` | string | Platform code |
| `.hasMore` | boolean | Indicates whether more data is available. |
| `.cursor` | string | Pagination cursor for retrieving next page of results |

## `GET /v1/links` — Tracking links, free trial links and profile promotions

| Field | Type | Description |
|---|---|---|
| `.data` | object |  |
| `.data.platformCode` | string | Platform code |
| `.data.linkType` | string | Link type |
| `.data.list` | array | The returned data object.  **Important Association Rules**: The linkTypefield in this object indicates the specific data structure type for all elements in the listarray. The corre |
| .data.list[] — variant **CampaignLinkModel** | | |
| `.data.list[].id` | string | Unique identifier |
| `.data.list[].message` | string | Link description |
| `.data.list[].type` | string | Target fan type enum: new, expired, both |
| `.data.list[].subCount` | integer | Current number of subscribers |
| `.data.list[].subLimit` | integer | Subscription limit (`0` means no limit) |
| `.data.list[].subDuration` | integer | Subscription duration (in days) |
| `.data.list[].discount` | integer | Discount percentage (e.g., `30` represents `30%`) |
| `.data.list[].finishedFlag` | boolean | Link completion flag |
| `.data.list[].earningsGross` | integer | Gross earnings (in the smallest unit of the currency)  |
| `.data.list[].earningsNet` | integer | Net earnings (after deducting OnlyFans platform fees, in the smallest unit of the currency)  |
| `.data.list[].payingFansCount` | integer | Paying fans count (includes subscription earnings) |
| `.data.list[].currency` | string | Currency code |
| `.data.list[].createdTime` | string | Link creation time (unix timestamp in milliseconds) |
| `.data.list[].expiredTime` | string | Link expiration time (unix timestamp in milliseconds)  |
| `.data.list[].updatedTime` | string | Infloww last update time (Unix millisecond timestamp) |
| .data.list[] — variant **TrialLinkModel** | | |
| `.data.list[].id` | string | Unique identifier |
| `.data.list[].name` | string | Link name |
| `.data.list[].code` | string | The URL is constructed by concatenating this `code` with the following format:  OF domain + current creator name + `code`  For example, creator name: xxx,  code:123  Link URL: `htt |
| `.data.list[].subDuration` | integer | Trial duration (in days) |
| `.data.list[].subLimit` | integer | Subscription limit (`0` means no limit) |
| `.data.list[].subCount` | integer | Current number of subscribers |
| `.data.list[].finishedFlag` | boolean | Link completion flag |
| `.data.list[].source` | string | Link source |
| `.data.list[].autoDefaultList` | boolean | Whether to automatically move subscribed fans to a default list - true: yes - false: no |
| `.data.list[].defaultListName` | string | Default fan list name |
| `.data.list[].relTagNames` | array | Related tag names |
| `.data.list[].spendClaim` | string | Percentage of fans who claimed a free trial that purchased subscriptions, spent on content, or gave tips |
| `.data.list[].payingFansCount` | integer | Number of fans who purchased subscriptions, spent on content, or gave tips |
| `.data.list[].earningsGross` | integer | Gross earnings (in the smallest unit of the currency) |
| `.data.list[].earningsNet` | integer | Net earnings (after deducting OnlyFans platform fees, in the smallest unit of the currency) |
| `.data.list[].aepsGross` | number | Average gross earnings per subscriber (`EarningsGross` ÷ number of subscribers) |
| `.data.list[].aepsNet` | integer | Average net earnings per subscriber (`EarningsNet` ÷ number of subscribers) |
| `.data.list[].currency` | string | Currency code |
| `.data.list[].createdTime` | string | Link creation time (unix timestamp in milliseconds) |
| `.data.list[].expiredTime` | string | Link expiration time (unix timestamp in milliseconds)  |
| `.data.list[].updatedTime` | string | Infloww last update time (unix timestamp in milliseconds) |
| .data.list[] — variant **TrackingLinkModel** | | |
| `.data.list[].id` | string | Unique identifier |
| `.data.list[].name` | string | Link name |
| `.data.list[].code` | string | The URL is constructed by concatenating this `code` with the following format:  OF domain + current creator name + **'c'** + `code`  For example, creator name: xxx,  code:123  Link |
| `.data.list[].clickCount` | integer | Click count |
| `.data.list[].subCount` | integer | Current number of subscribers |
| `.data.list[].finishedFlag` | boolean | Link completion flag |
| `.data.list[].source` | string | Link source |
| `.data.list[].autoDefaultList` | boolean | Whether to automatically move subscribed fans to a default list - true: yes - false: no |
| `.data.list[].defaultListName` | string | Default fan list name |
| `.data.list[].relTagNames` | array | Related tag names |
| `.data.list[].earningsGross` | integer | Gross earnings (in the smallest unit of the currency) |
| `.data.list[].earningsNet` | integer | Net earnings (after deducting OnlyFans platform fees, in the smallest unit of the currency) |
| `.data.list[].payingFansCount` | integer | Number of fans who spent on content or gave tips |
| `.data.list[].subscriptionCVR` | string | Subscription conversion rate (percentage of clicks converted to subscribers) |
| `.data.list[].spendingCVR` | string | Spending conversion rate: Percentage of fans who spent on content or gave tips |
| `.data.list[].epcGross` | integer | Earnings per click (gross, `EarningsGross` ÷ number of clicks) |
| `.data.list[].epcNet` | number | Earnings per click (net, after deducting OnlyFans platform fees, `EarningsNet` ÷ number of clicks)  |
| `.data.list[].aepsGross` | integer | Average gross earnings per subscriber (`EarningsGross` ÷ number of subscribers) |
| `.data.list[].aepsNet` | integer | Average net earnings per subscriber (`EarningsNet` ÷ number of subscribers) |
| `.data.list[].currency` | string | currency |
| `.data.list[].createdTime` | string | Link creation time (unix timestamp in milliseconds) |
| `.data.list[].expiredTime` | string | Link expiration time (unix timestamp in milliseconds)  |
| `.data.list[].updatedTime` | string | Infloww last update time （unix timestamp in milliseconds） |
| `.hasMore` | boolean | Indicates whether more data is available. |
| `.cursor` | string | Pagination cursor for retrieving next page of results |

## `GET /v1/linkfans` — Fans from tracking links, free trial links and profile promotions

| Field | Type | Description |
|---|---|---|
| `.data` | object |  |
| `.data.list` | array |  |
| `.data.list[].id` | string | Unique identifier(Link ID) |
| `.data.list[].fanId` | string | Fan ID |
| `.data.list[].fanName` | string | Fan name |
| `.data.list[].subscriptionEarningGross` | integer | Subscription earnings (gross, in the smallest unit of the currency) |
| `.data.list[].subscriptionEarningNet` | integer | Subscription earnings after deducting OnlyFans fees (in the smallest unit of the currency) |
| `.data.list[].postsEarningGross` | integer | Post earnings (gross, in the smallest unit of the currency) |
| `.data.list[].postsEarningNet` | integer | Post earnings after deducting OnlyFans fees (in the smallest unit of the currency) |
| `.data.list[].messagesEarningGross` | integer | Message earnings (gross, in the smallest unit of the currency)  |
| `.data.list[].messagesEarningNet` | integer | Message earnings after deducting OnlyFans fees (in the smallest unit of the currency)  |
| `.data.list[].streamsEarningGross` | integer | Stream earnings (gross, in the smallest unit of the currency) |
| `.data.list[].streamsEarningNet` | integer | Stream earnings after deducting OnlyFans fees (in the smallest unit of the currency) |
| `.data.list[].tipsEarningGross` | integer | Tip earnings (gross, in the smallest unit of the currency) |
| `.data.list[].tipsEarningNet` | integer | Tip earnings after deducting OnlyFans fees (in the smallest unit of the currency) |
| `.data.list[].currency` | string | Currency code |
| `.data.list[].subscribedTime` | string | Subscription time (unix timestamp in milliseconds) |
| `.data.linkType` | string | Link type |
| `.data.platformCode` | string | Platform code |
| `.hasMore` | boolean | Indicates whether more data is available. |
| `.cursor` | string | Indicates whether more data is available. |

## `GET /v1/automated-messages` — Automated messages

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].automatedMessageId` | integer | Unique identifier for the automated message |
| `.data.list[].employeeId` | integer | Employee ID who configured the message |
| `.data.list[].status` | string | Message status enum: Scheduled, Active, Completed, Canceled |
| `.data.list[].includeListNames` | array | Fan list names to include |
| `.data.list[].excludeListNames` | array | Fan list names to exclude |
| `.data.list[].totalSpendMin` | number | Minimum total spend filter (in the smallest unit of the currency) |
| `.data.list[].totalSpendMax` | number | Maximum total spend filter (in the smallest unit of the currency) |
| `.data.list[].tipsGreaterThan` | number | Minimum tips amount filter (in the smallest unit of the currency) |
| `.data.list[].subscribeDurationGreaterThan` | number | Minimum subscription duration filter (in months) |
| `.data.list[].excludeCreators` | boolean | Whether to exclude creators from the target audience |
| `.data.list[].messageCdHours` | number | Cooldown period between messages (in hours) |
| `.data.list[].excludeFansWUnreadMessages` | boolean | Whether to exclude fans with unread messages |
| `.data.list[].excludeFansWViewSameMedia` | boolean | Whether to exclude fans who viewed the same media |
| `.data.list[].onlyOnlineFans` | boolean | Whether to target only online fans |
| `.data.list[].trigger` | number | Message trigger type. Possible values: - `1` — Nudge (messages fans when they comes online) - `2` — Subscriber welcome (greet fan when they subscribe) - `3` — Purchases (follow up  |
| `.data.list[].triggerFrequency` | number | Trigger evaluation frequency. - `1` — Once - `2` — Every time |
| `.data.list[].collections` | array | Message collections with scripts and performance metrics |
| `.data.list[].collections[].collectionNo` | number | Collection sequence number |
| `.data.list[].collections[].messages` | array | Script messages in this collection |
| `.data.list[].collections[].price` | number | Total price of all messages in this collection (in the smallest unit of the currency) |
| `.data.list[].collections[].numberOfTimesSent` | number | Number of times this collection was sent |
| `.data.list[].collections[].numberOfPurchases` | number | Number of purchases generated by this collection |
| `.data.list[].collections[].revenue` | number | Revenue generated by this collection (in the smallest unit of the currency) |
| `.data.list[].price` | number | Total price of all messages across all collections (in the smallest unit of the currency) |
| `.data.list[].canceledByEmployeeId` | number | ID of the employee who canceled the message |
| `.data.list[].totalNumberOfTimeSent` | number | Total number of times the message was sent |
| `.data.list[].totalNumberOfPurchases` | number | Total number of purchases generated |
| `.data.list[].totalRevenue` | number | Total revenue generated (in the smallest unit of the currency) |
| `.data.list[].sentTime` | string | Time when the message was sent (unix timestamp in milliseconds) |
| `.data.list[].endTime` | string | Time when the message campaign ended (unix timestamp in milliseconds) |
| `.data.list[].createdTime` | string | Creation time (unix timestamp in milliseconds) |
| `.data.list[].modifiedTime` | string | Last modification time (unix timestamp in milliseconds) |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/priority-mass-messages` — Priority mass messages

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].priorityMassMessageId` | number | Unique identifier for the priority mass message |
| `.data.list[].employeeId` | number | Employee ID who configured the message |
| `.data.list[].status` | string | Message status enum: Scheduled, Active, Completed, Canceled |
| `.data.list[].includeListNames` | array | Fan list names to include |
| `.data.list[].excludeListNames` | array | Fan list names to exclude |
| `.data.list[].totalSpendMin` | number | Minimum total spend filter (in the smallest unit of the currency) |
| `.data.list[].totalSpendMax` | number | Maximum total spend filter (in the smallest unit of the currency) |
| `.data.list[].tipsGreaterThan` | number | Minimum tips amount filter (in the smallest unit of the currency) |
| `.data.list[].subscribeDurationGreaterThan` | number | Minimum subscription duration filter (in months) |
| `.data.list[].excludeCreators` | boolean | Whether to exclude creators from the target audience |
| `.data.list[].messageCdHours` | number | Cooldown period between messages (in hours) |
| `.data.list[].excludeFansWUnreadMessages` | boolean | Whether to exclude fans with unread messages |
| `.data.list[].excludeFansWViewSameMedia` | boolean | Whether to exclude fans who viewed the same media |
| `.data.list[].onlyOnlineFans` | boolean | Whether to target only online fans |
| `.data.list[].collection` | object | Message collection with scripts and performance metrics |
| `.data.list[].collection.collectionNo` | number | Collection sequence number |
| `.data.list[].collection.messages` | array | Script messages in this collection |
| `.data.list[].collection.messages[].messageContent` | string | Message script content |
| `.data.list[].collection.messages[].price` | number | Message price (in the smallest unit of the currency) |
| `.data.list[].collection.price` | number | Total price of all messages in this collection (in the smallest unit of the currency)  |
| `.data.list[].collection.numberOfTimesSent` | number | Number of times this collection was sent |
| `.data.list[].collection.numberOfPurchases` | number | Number of purchases generated by this collection |
| `.data.list[].collection.revenue` | number | Revenue generated by this collection (in the smallest unit of the currency) |
| `.data.list[].price` | number | Total price of all messages across all collections (in the smallest unit of the currency) |
| `.data.list[].unsentType` | number | Reason code for why the message was not sent. - `1` — Manual (manually unsent by employee) - `2` — Auto (automatically unsent by system) |
| `.data.list[].unsentByEmployeeId` | number | ID of the employee who marked the message as unsent |
| `.data.list[].canceledByEmployeeId` | number | ID of the employee who canceled the message |
| `.data.list[].totalNumberOfTimeSent` | number | Total number of times the message was sent |
| `.data.list[].totalNumberOfPurchases` | number | Total number of purchases generated |
| `.data.list[].totalRevenue` | number | Total revenue generated (in the smallest unit of the currency) |
| `.data.list[].sentTime` | string | Time when the message was sent (unix timestamp in milliseconds) |
| `.data.list[].endTime` | string | Time when the message campaign ended (unix timestamp in milliseconds) |
| `.data.list[].createdTime` | string | Creation time (unix timestamp in milliseconds) |
| `.data.list[].modifiedTime` | string | Last modification time (unix timestamp in milliseconds) |
| `.data.list[].failReason` | string | Reason for message failure |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/transaction-perf/details` — Sales records (all creators)

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].id` | integer | Unique identifier (Infloww employee sales ID) |
| `.data.list[].transactionId` | string | Infloww transaction ID |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].fanId` | string | Fan ID |
| `.data.list[].fanName` | string | Fan name |
| `.data.list[].createdTime` | string | Transaction creation time (ISO 8601 date-time in UTC) |
| `.data.list[].type` | string | Transaction type enum: Unknown, Subscription, RecurringSubscription, Tips, Messages, Referrals, Streams, Posts |
| `.data.list[].tipSource` | string | Tip source enum: Unknown, Profile, Post, Chat, Stream, Story |
| `.data.list[].status` | string | Transaction status enum: loading, done, undo, pending_return |
| `.data.list[].amount` | integer | Transaction amount (in the smallest unit of the currency) |
| `.data.list[].fee` | integer | Fee amount (in the smallest unit of the currency) |
| `.data.list[].net` | integer | Net amount (in the smallest unit of the currency) |
| `.data.list[].salesRule` | string | Sales attribution rule enum: Unassigned, Message sender, Last chatter, Employee on shift, Manually reassigned |
| `.data.list[].attributeEmployeeId` | integer | Employee ID attributed with this sale |
| `.data.list[].salesAmount` | integer | Attributed sales amount (in the smallest unit of the currency) |
| `.data.list[].currency` | string | Currency code |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/invoice-data/monthly-billing` — Invoice

| Field | Type | Description |
|---|---|---|
| `.data` | object | Monthly billing summary data. |
| `.data.list` | array | List of monthly billing records. |
| `.data.list[].billingId` | string | Unique identifier for billing, used for querying billing details. |
| `.data.list[].invoiceId` | string | Invoice ID. Null if not yet invoiced. |
| `.data.list[].billingPeriod` | string | Billing period in yyyy-MM format. |
| `.data.list[].currency` | string | Currency code (USD or EUR). |
| `.data.list[].subscription` | integer | Original subscription fee. |
| `.data.list[].discount` | integer | Discount amount. |
| `.data.list[].igic` | integer | Tax amount. Null if no tax. |
| `.data.list[].total` | integer | Total amount. Equals realAmount when vat is null. |
| `.data.list[].deductions` | integer | Balance/Wallet deduction amount. |
| `.data.list[].balanceDue` | integer | Amount due after deductions. |
| `.data.list[].paid` | integer | Total paid amount across all payment channels. |
| `.data.list[].pending` | integer | Current remaining amount due (= balanceDue - paid). |

## `GET /v1/transaction-perf/manual-assignment/details` — Reassigned sales log

| Field | Type | Description |
|---|---|---|
| `.data` | object | Manual assignment records. |
| `.data.list` | array | List of manual assignment records. |
| `.data.list[].id` | integer | Unique identifier of the manual assignment record. |
| `.data.list[].transactionId` | integer | Infloww transaction ID. |
| `.data.list[].transactionPerfId` | integer | Infloww Sales Records ID. |
| `.data.list[].operationType` | string | Operation type. enum: Exclude, Include |
| `.data.list[].operationEmployeeId` | integer | ID of the employee who performed the operation. |
| `.data.list[].beforeAttributeEmployeeId` | integer | Employee ID before the operation. Null if no prior assignment. |
| `.data.list[].afterAttributeEmployeeId` | integer | Employee ID after the operation. Null if no assignment. |
| `.data.list[].createdTime` | string | Operation time (unix timestamp in milliseconds). |
| `.cursor` | string | Pagination cursor for retrieving next page of results (manual assignment record ID). |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/creator-report/chat-summary` — Messages sent statistics

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].replyTime` | integer | Average message reply time (in milliseconds) |
| `.data.list[].fansChatted` | integer | Number of unique fans who chatted |
| `.data.list[].messagesSent` | integer | Number of messages sent by the creator |
| `.data.list[].ppvsSent` | integer | Number of PPV messages sent by the creator |

## `GET /v1/creator-report/fans/count` — Fans' status

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].activeFans` | integer | Number of active fans |
| `.data.list[].expiredFans` | integer | Number of expired fans |

## `GET /v1/creator-report/fans/subscriber-count` — New and renewed fans

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].newSubscribers` | integer | Number of new subscribers |
| `.data.list[].subscriberRenewals` | integer | Number of subscription renewals |

## `GET /v1/creator-report/fans/renew-on` — Fans with renew on

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].fansWithRenewOn` | integer | Number of fans with auto-renew enabled |

## `GET /v1/creator-report/fans/avg-subscription-length` — Fans' subscription length

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].avgSubscriptionLength` | integer | Average subscription length (in days) |

## `GET /v1/creator-report/reach/profile-visitor-count` — Profile visitors

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].profileVisitors` | integer | Total number of profile visitors |
| `.data.list[].guestProfileVisitors` | integer | Number of guest (not logged in) profile visitors |
| `.data.list[].loggedInUsersProfileVisitors` | integer | Number of logged-in profile visitors |

## `GET /v1/creator-report/rank` — Platform ranking

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].performanceRank` | number | Performance ranking |

## `GET /v1/creator/status-change-log` — Creator Infloww status log

| Field | Type | Description |
|---|---|---|
| `.data` | object | Creator status change log data. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array | List of status change log entries. |
| `.data.list[].id` | integer | Unique identifier of the status change log. |
| `.data.list[].statusBefore` | string | Status before the change. enum: connected, 2FA, not connect, disconnected |
| `.data.list[].statusAfter` | string | Status after the change. enum: connected, 2FA, not connect, disconnected |
| `.data.list[].creatorId` | integer | Creator ID. |
| `.data.list[].platformPid` | string | Platform performer ID. |
| `.data.list[].operationTime` | string | Operation time (unix timestamp in milliseconds). |
| `.data.list[].operationEmployeeId` | integer | ID of the employee who performed the operation. Null for automatic operations (e.g., auto-disconnect). |
| `.cursor` | string | Pagination cursor for retrieving next page of results (status change log ID). |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/employees` — Employees

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].employeeId` | integer | Unique identifier for the employee |
| `.data.list[].employeeName` | string | Employee display name |
| `.data.list[].status` | string | Employee status enum: Activated, Deactivated, Deleted |
| `.data.list[].createdTime` | string | Creation time (unix timestamp in milliseconds) |
| `.data.list[].deletedTime` | string | Deletion time (unix timestamp in milliseconds). Null if the employee is still active. |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/employees/assigned-creators` — Employee's assigned creators

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].platformCode` | string | Platform code |
| `.data.list[].employeeId` | number | Unique identifier for the employee. |
| `.data.list[].creatorId` | number | Unique identifier for the creator. |
| `.cursor` | string | Pagination cursor for retrieving next page of results |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/employee-report/employee-sales-summary` — Sales statistics

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].employeeId` | integer | Unique identifier for the employee |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].salesAmount` | integer | Total sales generated according to your sales settings (in the smallest unit of the currency) |
| `.data.list[].ppvSalesAmount` | integer | Sales generated from PPVs (in the smallest unit of the currency) |
| `.data.list[].tipsSalesAmount` | integer | Sales generated from tips (in the smallest unit of the currency) |
| `.data.list[].directMessageSalesAmount` | integer | Sales from direct messages sent by the employee, excluding priority/OF mass messages and automated messages (in the smallest unit of the currency) |
| `.data.list[].priorityMassMessageSalesAmount` | integer | Sales generated from priority mass messages (in the smallest unit of the currency) |
| `.data.list[].massMessageSalesAmount` | integer | Sales generated from OF mass messages (in the smallest unit of the currency) |
| `.data.list[].currency` | string | Currency code |

## `GET /v1/employee-report/employee-chat-summary` — Chatting statistics

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.platformCode` | string | Platform code |
| `.data.list` | array |  |
| `.data.list[].employeeId` | integer | Unique identifier for the employee |
| `.data.list[].date` | string | Statistics date in ISO 8601 format (YYYY-MM-DD). Example: 2026-02-27 |
| `.data.list[].platformPid` | integer | Platform performer ID |
| `.data.list[].directMessagesSent` | integer | Number of direct messages sent by the employee (excluding priority/OF mass and automated messages) |
| `.data.list[].directPpvsSent` | integer | Number of PPVs sent via direct messages (excluding priority/OF mass and automated messages) |
| `.data.list[].goldenRatio` | string | Percentage of direct messages that are PPVs (directPpvsSent / directMessagesSent × 100) |
| `.data.list[].ppvsUnlocked` | integer | Number of direct PPVs unlocked by fans |
| `.data.list[].unlockRate` | string | Percentage of direct PPVs unlocked by fans (ppvsUnlocked / directPpvsSent × 100) |
| `.data.list[].fansChatted` | integer | Number of unique fans the employee sent at least one message to |
| `.data.list[].characterCount` | integer | Total character count of messages sent (excluding priority/OF mass, automated, and script-based messages) |
| `.data.list[].responseTimeBasedOnScheduledHours` | integer | V1.4: Average time taken by employee to reply to a fan in chat for messages sent during scheduled shift hours. Does not include unreplied messages. If multiple employees are assign |
| `.data.list[].responseTimeBasedOnClockedHours` | integer | V1.4: Average time taken by employee to reply to a fan based on clocked hours. Does not include unreplied messages (in milliseconds). |

## `GET /v1/scripts` — Scripts

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].id` | number | Unique identifier for the script |
| `.data.list[].name` | string | Script name |
| `.cursor` | string | Pagination cursor for retrieving next page of results. Null if no more data is available. |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/script/statistics` — Script statistics

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.sendCount` | number | Total number of times the script was sent |
| `.data.payUsedCount` | number | Total number of paid sends |
| `.data.purchaseCount` | number | Total number of purchases generated |
| `.data.revenueAmount` | number | Total revenue generated (in cents) |

## `GET /v1/script-tag` — Scripts' tags

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].id` | number | Unique identifier for the script tag |
| `.data.list[].tagName` | string | Script tag name |
| `.cursor` | string | Pagination cursor for retrieving next page of results. Null if no more data is available. |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/script-tag/statistics` — Scripts' tag statistics

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.sendCount` | number | Total number of times the script was sent |
| `.data.payUsedCount` | number | Total number of paid sends |
| `.data.purchaseCount` | number | Total number of purchases generated |
| `.data.revenueAmount` | number | Total revenue generated (in cents) |

## `GET /v1/script-sequence` — Sequence

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.list` | array |  |
| `.data.list[].id` | number | Unique identifier for the script sequence |
| `.data.list[].name` | string | Script sequence name |
| `.data.list[].description` | ['string', 'null'] | Script sequence description |
| `.cursor` | string | Pagination cursor for retrieving next page of results. Null if no more data is available. |
| `.hasMore` | boolean | Indicates whether more data is available. |

## `GET /v1/script-sequence/statistics` — Sequence statistics

| Field | Type | Description |
|---|---|---|
| `.data` | object | Returned upon success, corresponding to the specific business data structure. |
| `.data.sendCount` | number | Total number of times the script was sent |
| `.data.payUsedCount` | number | Total number of paid sends |
| `.data.purchaseCount` | number | Total number of purchases generated |
| `.data.revenueAmount` | number | Total revenue generated (in cents) |

