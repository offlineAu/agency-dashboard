# API Connection Report

Generated: 2026-11-21 07:06:45 UTC  
Base URL: `https://openapi.infloww.com`  
Auth: `Authorization: <raw key>` + `x-oid: <agency OID>` (values not recorded)  
Result: **27/27 probes succeeded**

Probe window: last 7 complete UTC days. Only GET requests were sent. No fan names or IDs are recorded here.

| Probe | Endpoint | Status | ms | Records | hasMore | Fields / error |
|---|---|---|---|---|---|---|
| Connected creators | `/v1/creators` | 200 | 1100 | 8 | False | createdTime, id, name, nickName, platformPid, tagName, userName |
| All creators | `/v1/all-creators` | 200 | 306 | 14 | False | createdTime, deletedTime, id, name, nickName, platformPid, status, tagName, userName |
| Employees | `/v1/employees` | 200 | 305 | 100 | True | createdTime, deletedTime, employeeId, employeeName, status |
| Assigned creators | `/v1/employees/assigned-creators` | 200 | 302 | 0 | False | list |
| Transactions | `/v1/transactions` | 200 | 324 | 0 | False | list, platformCode |
| Refunds | `/v1/refunds` | 200 | 321 | 0 | False | list, platformCode |
| Sales records | `/v1/transaction-perf/details` | 200 | 406 | 0 | False | list, platformCode |
| Links TRACKING | `/v1/links` | 200 | 359 | 0 | False | linkType, list, platformCode |
| Links TRIAL | `/v1/links` | 200 | 363 | 0 | False | linkType, list, platformCode |
| Links CAMPAIGN | `/v1/links` | 200 | 344 | 0 | False | linkType, list, platformCode |
| Automated messages | `/v1/automated-messages` | 200 | 309 | 1 | False | automatedMessageId, canceledByEmployeeId, collections, createdTime, employeeId, endTime, excludeCreators, excludeFansWUnreadMessages, excludeFansWViewSameMedia, excludeListNames, includeListNames, messageCdHours, modifiedTime, onlyOnlineFans, price, sentTime, status, subscribeDurationGreaterThan, tipsGreaterThan, totalNumberOfPurchases, totalNumberOfTimeSent, totalRevenue, totalSpendMax, totalSpendMin, trigger, triggerFrequency |
| Priority mass messages | `/v1/priority-mass-messages` | 200 | 302 | 0 | False | list, platformCode |
| Script tags | `/v1/script-tag` | 200 | 336 | 9 | False | id, tagName |
| Script sequences | `/v1/script-sequence` | 200 | 323 | 0 | False | list |
| Fans count (repeat-array) | `/v1/creator-report/fans/count` | 200 | 348 | 14 | None | activeFans, date, expiredFans, platformPid |
| Fans count (comma-array) | `/v1/creator-report/fans/count` | 200 | 386 | 14 | None | activeFans, date, expiredFans, platformPid |
| chat-summary | `/v1/creator-report/chat-summary` | 200 | 438 | 1 | None | fansChatted, messagesSent, platformPid, ppvsSent, replyTime |
| subscriber-count | `/v1/creator-report/fans/subscriber-count` | 200 | 341 | 7 | None | date, newSubscribers, platformPid, subscriberRenewals |
| renew-on | `/v1/creator-report/fans/renew-on` | 200 | 343 | 0 | None | list, platformCode |
| avg-subscription-length | `/v1/creator-report/fans/avg-subscription-length` | 200 | 327 | 7 | None | avgSubscriptionLength, date, platformPid |
| profile-visitor-count | `/v1/creator-report/reach/profile-visitor-count` | 200 | 328 | 7 | None | date, guestProfileVisitors, loggedInUsersProfileVisitors, platformPid, profileVisitors |
| rank | `/v1/creator-report/rank` | 200 | 316 | 7 | None | date, performanceRank, platformPid |
| Status change log | `/v1/creator/status-change-log` | 200 | 305 | 0 | False | list, platformCode |
| Employee sales summary | `/v1/employee-report/employee-sales-summary` | 200 | 327 | 0 | None | list, platformCode |
| Employee chat summary | `/v1/employee-report/employee-chat-summary` | 200 | 343 | 0 | None | list, platformCode |
| Manual assignments | `/v1/transaction-perf/manual-assignment/details` | 200 | 330 | 31 | False | afterAttributeEmployeeId, beforeAttributeEmployeeId, createdTime, id, operationEmployeeId, operationType, transactionId, transactionPerfId |
| Invoices (yyyy-MM) | `/v1/invoice-data/monthly-billing` | 200 | 301 | 2 | None | balanceDue, billingId, billingPeriod, currency, deductions, discount, igic, invoiceId, paid, pending, subscription, total |

## Findings

- Array encoding: repeat -> 2 creators returned, comma -> 2 creators returned (requested 2). Recommended INFLOWW_ARRAY_STYLE=repeat
- chat-summary for 1 creator over 7 days returned 1 row(s) (one aggregate row; fields: ['fansChatted', 'messagesSent', 'platformPid', 'ppvsSent', 'replyTime'])
- Invoice month format: yyyy-MM accepted
