# PostgreSQL移行 方式Q 棚卸し

- 作成日: 2026-10-20
- 位置づけ: `仕様書/PostgreSQL移行計画書_v3.md` §3-2-2(方式Qの実行前の棚卸し)の実施結果。読み取り調査のみ、コード変更・DB変更は行っていない
- 状態: 棚卸し(調査)は完了。対応方針は**提案のみ・未承認・未実施**。実施にはBOSSの承認が必要(移行計画書v3の運用ルールに従う)

---

## 1. 全体サマリー

| 項目 | 件数 |
|---|---|
| 対象アプリ数 | 14(ai, accounts, consumables, masters, notifications, orders, outsource, overtime, production, purchase, quality, shifts, shipping, system_settings) |
| 総モデル数(抽象基底クラス除く) | **238** |
| ユニークdb_table数 | **226** |
| db_tableが物理的に重複作成されている件数(要対応) | **12**(production 9・shipping 3) |
| 同様のパターンだが正しく回避済み(参考・対応不要) | 3(quality 2・ai 1) |
| migrationsフォルダが無いアプリ | 0件(全アプリに整備済み) |
| 対象外と確認したアプリ | `ocr`(models/migrationsともに無し)、`proposals`(2026-10-20削除済み) |
| RunSQL呼び出し数(実測) | **38箇所/34ファイル**(背景にあった「29/26」という数値とは不一致。本書の値を正とする。差異の原因は未調査) |
| うちPG書き換えが必要 | 7件(JSON系4、TINYINT(1)系2、DROP FOREIGN KEY系1) |
| うち書き換え不要(標準SQLのみ) | 31件 |
| DEFINER句を使うビュー | 0件(マイグレーション内では使用なし。`pm_ai_view_owner`は別の管理コマンド側と推測、未確認) |

---

## 2. db_table重複問題の確定一覧

### 2-1. 要対応(12件): production/shipping側が「通常のCreateModel」で再作成している

全件、`orders`側の実テーブル作成migrationと、`production`または`shipping`側の`0001_initial.py`(状態移管ではなく実DDL付き)が衝突している。`orders/migrations/0042_remove_migrated_models.py`は正しく`SeparateDatabaseAndState(database_operations=[])`でstateのみ削除しているため、**原因は受け皿側(production/shipping)が0001_initialを作り直した際に通常のCreateModelにしてしまったこと**。

| db_table | 最初の実作成(orders) | 2件目の実作成(production/shipping) |
|---|---|---|
| t_line_demand | orders/migrations/0008_linedemand.py:13-36 | production/migrations/0001_initial.py:107-130 |
| line_backlog | orders/migrations/0011_linebacklog.py:13-27 | production/migrations/0001_initial.py:78-102 |
| t_line_status | orders/migrations/0016_linestatus_linerealtimerecord.py:15-29 | production/migrations/0001_initial.py:16-30 |
| t_line_realtime_record | orders/migrations/0016_linestatus_linerealtimerecord.py:32-49 | production/migrations/0001_initial.py:175-195 |
| t_process_realtime_record | orders/migrations/0019_processrealtimerecord.py:15-35 | production/migrations/0001_initial.py:200-220 |
| t_line_gantt_plan | orders/migrations/0020_line_gantt_plan.py:13-29 | production/migrations/0001_initial.py:135-151 |
| t_stock_allocation | orders/migrations/0015_add_production_models.py:15-31 | production/migrations/0001_initial.py:33-49 |
| t_production_order | orders/migrations/0015_add_production_models.py:34-57 | production/migrations/0001_initial.py:52-75 |
| t_process_actual | orders/migrations/0015_add_production_models.py:60-79 | production/migrations/0001_initial.py:225-244 |
| t_shipment_actual | orders/migrations/0034_shipmentactual_shipmentactualhistory_and_more.py:15-33 | shipping/migrations/0001_initial.py:17-35 |
| t_shipment_actual_history | orders/migrations/0034_shipmentactual_shipmentactualhistory_and_more.py:36-53 | shipping/migrations/0001_initial.py:38-55 |
| t_delivery_progress | orders/migrations/0036_deliveryprogress.py:15-31 | shipping/migrations/0001_initial.py:77-93 |

production/0001_initial.pyは2026-01-12生成、shipping/0001_initial.pyは2026-05-20生成。いずれもordersへのmigration依存が無いため、空DBへの全migration適用順序次第(productionは順序不定、shippingは依存関係上ordersが確実に先行するため確定的)で「relation already exists」エラーになる。

### 2-2. 正しく回避済み(参考・対応不要)

| db_table | 実テーブル作成 | 状態移管(state-only) |
|---|---|---|
| t_scrap_record | orders/migrations/0021_scraprecord.py:13-32 | quality/migrations/0005_initial.py:24-57(`SeparateDatabaseAndState(database_operations=[])`) |
| t_scrap_record_detail | orders/migrations/0024_scraprecorddetail.py:13-33 | quality/migrations/0005_initial.py:61-82(同上) |
| ai_search_config | production/migrations/0112_add_ai_search_config.py:11-32 | ai/migrations/0001_initial.py:17-44(同上)、production/migrations/0113で同様にstate-only削除 |

**結論**: 同じ「アプリ間モデル移管」のパターンで、quality・aiは正しく`SeparateDatabaseAndState`を使い物理的な重複が無い。**production・shippingの2アプリだけが対応を誤っている**ことが明確になった。

---

## 3. 全モデル・db_table・作成migration対応表(app別)

> 238モデル全件。「作成migration」は実際にDB操作を伴うCreateModelがある箇所(state-onlyは除く)。2-1の★印は重複対象。

### ai(12モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| AISearchConfig | ai_search_config | production/migrations/0112_add_ai_search_config.py:11-32(実DDル) |
| AIConversation | ai_conversation | ai/migrations/0010_aiconversation.py:31 |
| AIAnalysisRun | ai_analysis_run | ai/migrations/0024_aianalysisrun.py:58 |
| AIAnalysisTemplate | ai_analysis_template | ai/migrations/0027_aianalysistemplate.py:51 |
| AIAnalysisTemplateNotification | ai_analysis_template_notification | ai/migrations/0029_aianalysistemplatenotification.py:33 |
| AIProviderConfig | ai_provider_config | ai/migrations/0002_ai_management_settings.py:78 |
| AIToolPolicy | ai_tool_policy | ai/migrations/0002_ai_management_settings.py:90 |
| AIDataPolicy | ai_data_policy | ai/migrations/0002_ai_management_settings.py:52 |
| AIAnalysisExecutionPolicy | ai_analysis_execution_policy | ai/migrations/0022_aianalysisexecutionpolicy.py:32 |
| AIKnowledgeSource | ai_knowledge_source | ai/migrations/0002_ai_management_settings.py:66 |
| AIKnowledgeDocument | ai_knowledge_document | ai/migrations/0008_aiknowledgedocument.py:20 |
| AICrossScreenAccessPolicy | ai_cross_screen_access_policy | ai/migrations/0019_aicrossscreenaccesspolicy.py:19 |

### accounts(13モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| Department | accounts_department | accounts/migrations/0002_department_userprofile.py:28 |
| UserProfile | accounts_userprofile | accounts/migrations/0002_department_userprofile.py:52 |
| UnitLineMapping | accounts_unit_line_mapping | accounts/migrations/0024_grouplinemapping.py:29 |
| UserSmtpConfig | accounts_user_smtp_configs | accounts/migrations/0001_initial.py:15-28(当初`user_smtp_configs`、0003でリネーム) |
| UserPermission | accounts_userpermission | accounts/migrations/0004_userpermission.py:23 |
| DepartmentPermission | accounts_departmentpermission | accounts/migrations/0005_department_position_permission.py:22 |
| PositionPermission | accounts_positionpermission | accounts/migrations/0005_department_position_permission.py:36 |
| DepartmentPositionPermission | accounts_department_position_permission | accounts/migrations/0006_department_position_permission.py:23 |
| UserFavorite | accounts_user_favorite | accounts/migrations/0037_userfavorite.py:27 |
| ApprovalRouteConfig | accounts_approval_route_config | accounts/migrations/0053_alter_departmentpermission_resource_and_more.py:35-61 |
| ApprovalRequest | accounts_approval_request | accounts/migrations/0057_approval_request_step_task.py:33 |
| ApprovalStep | accounts_approval_step | accounts/migrations/0057_approval_request_step_task.py:51 |
| ApprovalTask | accounts_approval_task | accounts/migrations/0057_approval_request_step_task.py:70 |

### consumables(7モデル、OrgSnapshotMixinは抽象のため除外)

| モデル | db_table | 作成migration |
|---|---|---|
| ConsumableSupplier | t_consumable_supplier | consumables/migrations/0001_initial.py:62 |
| ConsumableOrderEmailConfig | t_consumable_order_email_config | consumables/migrations/0004_consumableorderemailconfig.py:29 |
| Consumable | t_consumable | consumables/migrations/0001_initial.py:41 |
| ConsumableRequest | t_consumable_request | consumables/migrations/0001_initial.py:120 |
| ConsumableDispatchOrder | t_consumable_dispatch_order | consumables/migrations/0001_initial.py:89 |
| ConsumableDispatchOrderItem | t_consumable_dispatch_order_item | consumables/migrations/0001_initial.py:144 |
| ConsumableStockMovement | t_consumable_stock_movement | consumables/migrations/0001_initial.py:174 |

### masters(32モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| Product | m_product | masters/migrations/0001_initial.py:83 |
| ProductStockLocation | m_product_stock_location | masters/migrations/0061_add_product_stock_location_table.py:26 |
| ProductCodeMapping | m_product_code_mapping | masters/migrations/0054_productcodemapping.py:25 |
| Customer | m_customer | masters/migrations/0001_initial.py:114 |
| Process | m_process | masters/migrations/0001_initial.py:61 |
| Line | m_line | masters/migrations/0001_initial.py:44 |
| Supplier | m_supplier | masters/migrations/0001_initial.py:96 |
| Calendar | m_calendar | masters/migrations/0001_initial.py:28 |
| WorkPattern | m_work_pattern | masters/migrations/0016_workpattern_calendarday_work_pattern.py:30 |
| BreakTime | m_break_time | masters/migrations/0017_remove_workpattern_break_minutes_and_more.py:41 |
| CalendarDay | m_calendar_day | masters/migrations/0001_initial.py:190 |
| BOM | m_bom | masters/migrations/0001_initial.py:132 |
| BOMItem | m_bom_item | masters/migrations/0001_initial.py:172 |
| Routing | m_routing | masters/migrations/0001_initial.py:151 |
| RoutingStep | m_routing_step | masters/migrations/0001_initial.py:213 |
| RoutingChangeHistory | t_routing_change_history | masters/migrations/0072_routingchangehistory.py:32 |
| RoutingStepMaterial | m_routing_step_material | masters/migrations/0008_routingstepmaterial.py:27 |
| ProcessCycleTime | m_process_cycle_time | masters/migrations/0012_add_process_cycle_time.py:33 |
| LineCycleTime | m_line_cycle_time | masters/migrations/0071_linecycletime.py:29 |
| ProductGroup | m_product_group | masters/migrations/0024_containercapacity_productgroup_product_capacity_and_more.py:45 |
| ContainerCapacity | m_container_capacity | masters/migrations/0024...py:28(0025で`container_capacity`へ改名→0026で`m_container_capacity`に戻す。実害なし) |
| ContainerCapacityImage | m_container_capacity_image | masters/migrations/0066_containercapacityimage.py:29 |
| ProductContainer | m_product_container | masters/migrations/0067_add_product_container.py:25 |
| Equipment | m_equipment | masters/migrations/0034_equipment.py:30 |
| KubotaSakaiTruck | m_kubota_sakai_truck | masters/migrations/0044_add_kubota_sakai_truck.py:35 |
| SupplierTruck | m_supplier_truck | masters/migrations/0078_suppliertruck.py:39 |
| Contact | m_contacts | masters/migrations/0028_contact.py:32 |
| MobileDevice | masters_mobiledevice(db_table未指定) | masters/migrations/0051_mobile_device.py:16-17 |
| MobileDeviceHistory | masters_mobiledevicehistory(db_table未指定) | masters/migrations/0082_mobiledevicehistory.py:14-15 |
| MobileDeviceInventory | masters_mobiledeviceinventory(db_table未指定) | masters/migrations/0051_mobile_device.py:41-42 |
| ManualDocument | masters_manualdocument(db_table未指定) | masters/migrations/0052_manual_document.py:16-17 |
| InterruptionReason | m_interruption_reason | masters/migrations/0088_interruptionreason.py:30 |

### notifications(8モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| Notification | notifications | notifications/migrations/0001_initial.py:29 |
| NotificationRead | notification_reads | notifications/migrations/0004_notification_read.py:27 |
| CallSession | call_sessions | notifications/migrations/0006_callsession_callsignal.py:31 |
| CallSignal | call_signals | notifications/migrations/0006_callsession_callsignal.py:49 |
| CallRecording | call_recordings | notifications/migrations/0009_callrecording.py:34 |
| PushSubscription | push_subscriptions | notifications/migrations/0007_pushsubscription.py:29 |
| NativePushToken | native_push_tokens | notifications/migrations/0008_nativepushtoken.py:30 |
| UserRequestTask | notifications_user_request_task | notifications/migrations/0011_user_request_task.py:33 |

### orders(19モデル、実体は`orders/core/models.py`)

| モデル | db_table | 作成migration |
|---|---|---|
| Order | t_order | orders/migrations/0001_initial.py:35 |
| OrderLine | t_order_line | orders/migrations/0001_initial.py:57 |
| KubotaSakaiDueSharedNote | t_kubota_sakai_due_shared_note | orders/migrations/0068_kubota_sakai_due_shared_note.py:25 |
| KubotaSakaiDueAdjustment | t_kubota_sakai_due_adjustment | orders/migrations/0046_kubotasakaidueadjustment.py:34 |
| KubotaSakaiDueAllocationOverride | t_kubota_sakai_due_allocation_override | orders/migrations/0063_kubotasakaidueallocationoverride.py:28 |
| KubotaSakaiTripAssignment | t_kubota_sakai_trip_assignment | orders/migrations/0048_kubotasakaitripassignment.py:32 |
| KubotaSakaiPseudoTruckProduct | m_kubota_sakai_pseudo_truck_product | orders/migrations/0054_kubota_sakai_pseudo_truck_product.py:26 |
| ShippingRun | t_shipping_run | orders/migrations/0052_shippingrun_shippingtrip_shippingtripallocation_and_more.py:32 |
| ShippingTrip | t_shipping_trip | orders/migrations/0052...py:54 |
| ShippingTripAllocation | t_shipping_trip_allocation | orders/migrations/0052...py:73 |
| ShippingTripNotice | t_shipping_trip_notice | orders/migrations/0058_shippingtripnotice.py:30 |
| StgOrderRaw | stg_order_raw | orders/migrations/0001_initial.py:83 |
| StgOrderRawTiera | stg_order_raw_tiera | orders/migrations/0030_alter_stgorderdaily_product_name_and_more.py:93 |
| StgOrderRawRieden | stg_order_raw_rieden | orders/migrations/0031_alter_stgorderdaily_raw_stgorderrawrieden_and_more.py:41 |
| StgOrderRawKubota | stg_order_raw_kubota | orders/migrations/0030...py:59 |
| StgOrderDaily | stg_order_daily | orders/migrations/0001_initial.py:108 |
| KubotaSakaiImportConfig | kubota_sakai_import_config | orders/migrations/0044_kubotasakaiimportconfig.py:26 |
| KubotaSakaiDueNotifyConfig | kubota_sakai_due_notify_config | orders/migrations/0064_kubota_sakai_due_notify_config.py:24 |
| FirstArticleNoticeLog | t_first_article_notice_log | orders/migrations/0056_first_article_notice_log.py:28 |

参考(現models.pyには無いが過去にordersで実テーブル作成され他appへ状態移管済み): LineDemand, LineBacklog, LineGanttPlan, LineStatus, LineRealtimeRecord, ProcessRealtimeRecord, StockAllocation, ProductionOrder, ProcessActual(→production、§2-1参照)/ ShipmentActual, ShipmentActualHistory, DeliveryProgress(→shipping、§2-1参照)/ ScrapRecord, ScrapRecordDetail(→quality、§2-2参照)。`t_line_plan`(orders/0005→0007で削除)は現行productionの`LinePlan`(`line_plan`)とは別物で無関係。

### outsource(13モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| Subcontractor | outsource_subcontractor | outsource/migrations/0001_initial.py:48 |
| OutsourceItem | outsource_item | outsource/migrations/0001_initial.py:29 |
| OutsourceMaterial | outsource_material | outsource/migrations/0007_add_outsource_material.py:31 |
| OutsourceBOM | outsource_bom | outsource/migrations/0001_initial.py:140 |
| OutsourceOrder | outsource_order | outsource/migrations/0001_initial.py:71 |
| OutsourceSplit | outsource_split | outsource/migrations/0001_initial.py:92 |
| MaterialRequirement | outsource_material_requirement | outsource/migrations/0001_initial.py:114 |
| SplitImportLog | outsource_split_import_log | outsource/migrations/0012_add_split_import_log.py:28 |
| SubcontractorDelivery | outsource_subcontractor_delivery | outsource/migrations/0003_add_delivery_shipment.py:46 |
| CustomerShipment | outsource_customer_shipment | outsource/migrations/0003_add_delivery_shipment.py:28 |
| MaterialStockTransaction | outsource_material_stock_tx | outsource/migrations/0009_stock_transactions.py:28 |
| ProductStockTransaction | outsource_product_stock_tx | outsource/migrations/0009_stock_transactions.py:49 |
| OutsourceFirstArticleNoticeLog | outsource_first_article_notice_log | outsource/migrations/0014_outsource_first_article_notice_log.py:25 |

### overtime(2モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| OvertimeApplication | t_overtime_application | overtime/migrations/0001_initial.py:67 |
| OvertimeApprovalLog | t_overtime_approval_log | overtime/migrations/0001_initial.py:111 |

### production(68モデル、★=§2-1の重複対象)

| モデル | db_table | 作成migration |
|---|---|---|
| LineDemand★ | t_line_demand | production/migrations/0001_initial.py:107-130 |
| ActualCycleTime | t_actual_cycle_time | production/migrations/0078_actualcycletime_finishedproductcycletime.py:32 |
| FinishedProductCycleTime | t_finished_product_cycle_time | production/migrations/0078...py:51 |
| AutoPlanAggregateSetting | t_auto_plan_aggregate_setting | production/migrations/0057_autoplanaggregatesetting.py:32 |
| BrakeLineRecord | brake_line_record | production/migrations/0039_brake_line_record.py:35 |
| CameraCountEvent | t_camera_count_event | production/migrations/0052_cameracountevent_productionresultdaily.py:34 |
| ProductionResultDaily | t_production_result_daily | production/migrations/0052...py:52 |
| DailyProcessTarget | t_daily_process_target | production/migrations/0088_daily_process_target.py:33 |
| GanttDisplayProductMap | t_gantt_display_product_map | production/migrations/0046_ganttdisplayproductmap.py:32 |
| GanttProcessDisplayOrder | t_gantt_process_display_order | production/migrations/0081_ganttprocessdisplayorder.py:28 |
| LaserActual | t_laser_actual | production/migrations/0034_laser_actual_models.py:42 |
| LaserActualDetail | t_laser_actual_detail | production/migrations/0034...py:64 |
| LaserShiftRecord | t_laser_shift_record | production/migrations/0038_replace_laser_equipment_daily_record_with_shift_record.py:26-78(旧t_laser_equipment_daily_recordをDeleteModel後に新規作成。重複なし) |
| LaserPattern | t_laser_pattern | production/migrations/0032_laser_pattern_models.py:29 |
| LaserPatternComponent | t_laser_pattern_component | production/migrations/0032...py:64 |
| LaserPatternFinishedProduct | t_laser_pattern_finished | production/migrations/0032...py:46 |
| LaserProcessingFreqPattern | t_laser_processing_freq_pattern | production/migrations/0096_laser_processing_freq_pattern.py:29 |
| LaserWeeklyPlanTarget | t_laser_weekly_plan_target | production/migrations/0092_laser_weekly_plan.py:17 |
| LaserWeeklyPlanManualQuantity | t_laser_weekly_plan_manual_quantity | production/migrations/0093_laser_weekly_plan_manual_quantity.py:17 |
| LaserWeeklyPatternManualQuantity | t_laser_weekly_pattern_manual_quantity | production/migrations/0094_laser_weekly_pattern_manual_quantity.py:31 |
| LaserWeeklyPatternInitialProgress | t_laser_weekly_pattern_initial_progress | production/migrations/0095_laser_weekly_initial_progress.py:24 |
| LaserWeeklyPatternDailyProgress | t_laser_weekly_pattern_daily_progress | production/migrations/0102_add_laser_weekly_pattern_daily_progress.py:23 |
| LaserWeeklyMaterialGroup | t_laser_weekly_material_group | production/migrations/0092...py:23 |
| LaserWeeklyMaterialOrderProgress | t_laser_weekly_material_order_progress | production/migrations/0097_laser_weekly_material_order_progress.py:24 |
| LaserMaterialReceipt | t_laser_material_receipt | production/migrations/0108_lasermaterialreceipt.py:34 |
| LaserWeeklyMaterialInitialProgress | t_laser_weekly_material_initial_progress | production/migrations/0098_laser_weekly_material_initial_progress.py:13 |
| LaserWeeklyMaterialDailyProgress | t_laser_weekly_material_daily_progress | production/migrations/0106_add_laser_weekly_material_daily_progress.py:24 |
| LaserMaterialOrderEmailConfig | t_laser_material_order_email_config | production/migrations/0103_lasermaterialorderemailconfig.py:26 |
| LineBacklog★ | line_backlog | production/migrations/0001_initial.py:78-102 |
| LineBacklogAdjustment | production_line_backlog_adjustment | production/migrations/0024_linebacklogadjustment.py:32 |
| LineDailyScheduleSetting | line_daily_schedule_setting | production/migrations/0002_add_line_daily_schedule_setting.py:27 |
| LineDefaultScheduleSetting | t_line_default_schedule_setting | production/migrations/0010_line_default_schedule_setting.py:29 |
| LineGanttPlan★ | t_line_gantt_plan | production/migrations/0001_initial.py:135-151 |
| LinePlan | line_plan | production/migrations/0001_initial.py:155-170(旧orders版`t_line_plan`とは別名で無関係) |
| LineProductDisplayOrder | t_line_product_display_order | production/migrations/0055_lineproductdisplayorder.py:29 |
| LineRealtimeRecord★ | t_line_realtime_record | production/migrations/0001_initial.py:175-195 |
| LineStatus★ | t_line_status | production/migrations/0001_initial.py:16-30 |
| MorningMeeting | t_morning_meeting | production/migrations/0072_morning_meeting.py:40 |
| MorningMeetingParticipant | t_morning_meeting_participant | production/migrations/0072...py:60 |
| MorningMeetingAttachment | t_morning_meeting_attachment | production/migrations/0073_morningmeetingattachment_and_more.py:42 |
| ProductionPlanChangeLog | production_plan_change_log | production/migrations/0004_add_production_plan_lock_setting_and_change_log.py:43 |
| PlanDeviationLineConfig | t_plan_deviation_line_config | production/migrations/0058_plan_deviation_line_config.py:22 |
| ProductionPlanLineSetting | production_plan_line_setting | production/migrations/0065_productionplanlinesetting.py:26 |
| ProductionPlanLockSetting | production_plan_lock_setting | production/migrations/0004...py:23 |
| ProcessRealtimeRecord★ | t_process_realtime_record | production/migrations/0001_initial.py:200-220 |
| ProcessWorkSession | t_process_work_session | production/migrations/0014_processworksession.py:43 |
| ProcessWorkSessionChangeHistory | t_process_work_session_change_history | production/migrations/0070_processworksessionchangehistory.py:37 |
| ProcessWorkSessionEquipment | t_process_work_session_equipment | production/migrations/0050_processworksessionequipment.py:28 |
| StockAllocation★ | t_stock_allocation | production/migrations/0001_initial.py:33-49 |
| ProductionOrder★ | t_production_order | production/migrations/0001_initial.py:52-75 |
| ProcessActual★ | t_process_actual | production/migrations/0001_initial.py:225-244 |
| ProductionActualReconcileReport | production_production_actual_reconcile_report | production/migrations/0048_alter_scheduleconfig_task_name_and_more.py:40 |
| ProductionActualReconcileReportDetail | production_production_actual_reconcile_report_detail | production/migrations/0048...py:62 |
| ProductionLock | production_lock | production/migrations/0104_production_lock.py:31 |
| ProgressMonitorTarget | production_progress_monitor_target | production/migrations/0122_progress_monitor_target.py:31 |
| PurchaseActualReconcileReport | production_purchase_actual_reconcile_report | production/migrations/0047_alter_scheduleconfig_task_name_and_more.py:40 |
| PurchaseActualReconcileReportDetail | production_purchase_actual_reconcile_report_detail | production/migrations/0047...py:62 |
| ProductionRecordConfirmation | t_production_record_confirmation | production/migrations/0049_record_confirmation.py:30 |
| ProductionRecordInquirySetting | production_record_inquiry_setting | production/migrations/0031_productionrecordinquirysetting.py:27 |
| RoutingMigrationLog | production_routing_migration_log | production/migrations/0030_routing_migration_log.py:34 |
| ScheduleConfig | production_schedule_config | production/migrations/0005_scheduleconfig_and_more.py:34 |
| ScheduleRunLog | production_schedule_run_log | production/migrations/0077_schedulerunlog.py:33 |
| SingleProcFinishedEntry | t_singleproc_finished_entry | production/migrations/0069_singleproc_finished_entry.py:32 |
| StocktakeRecord | production_stocktake_record | production/migrations/0059_stocktake_record.py:34 |
| StocktakeRecorder | production_stocktake_recorder | production/migrations/0061_add_stocktake_recorder.py:27 |
| StocktakeCounter | production_stocktake_counter | production/migrations/0083_stocktakecounter.py:22 |
| StocktakeArea | production_stocktake_area | production/migrations/0064_add_stocktake_area.py:26 |
| StocktakeLayoutConfig | production_stocktake_layout_config | production/migrations/0063_add_stocktake_layout_config.py:24 |

### purchase(19モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| PurchasePlanLockSetting | purchase_plan_lock_setting | purchase/migrations/0001_initial.py:24 |
| SupplierOrderPattern | supplier_order_pattern | purchase/migrations/0010_add_supplier_order_pattern.py:71 |
| SupplierOrderSchedule | supplier_order_schedule | purchase/migrations/0007_purchaseorderapprovalconfig_purchaseorderproposal_and_more.py:113 |
| PurchaseOrderProposal | purchase_order_proposal | purchase/migrations/0007...py:47 |
| PurchaseOrderProposalLine | purchase_order_proposal_line | purchase/migrations/0007...py:80 |
| PurchaseOrderProposalApproval | purchase_order_proposal_approval | purchase/migrations/0007...py:62 |
| PurchaseOrderTask | purchase_order_task | purchase/migrations/0007...py:96 |
| PurchasePlanChangeLog | purchase_plan_change_log | purchase/migrations/0001_initial.py:44 |
| EngineeringChangeCase | engineering_change_case | purchase/migrations/0003_engineeringchangecase_engineeringchangepart_and_more.py:26 |
| EngineeringChangePart | engineering_change_part | purchase/migrations/0003...py:42 |
| DiscontinuationCase | discontinuation_case | purchase/migrations/0038_discontinuation_models.py:36 |
| DiscontinuationProduct | discontinuation_product | purchase/migrations/0038...py:52 |
| DiscontinuationPart | discontinuation_part | purchase/migrations/0038...py:66 |
| PurchaseAutoDeliveryListConfig | purchase_auto_delivery_list_config | purchase/migrations/0016_auto_delivery_list_config.py:36 |
| PurchaseAutoOrderSendConfig | purchase_auto_order_send_config | purchase/migrations/0024_purchaseautoordersendconfig.py:39 |
| PurchaseAutoOrderSendHistory | purchase_auto_order_send_history | purchase/migrations/0031_purchaseautoordersendhistory.py:37 |
| PurchaseOrderProposalEmailConfig | purchase_order_proposal_email_config | purchase/migrations/0036_purchaseorderproposalemailconfig.py:28 |
| PurchaseAutoOrderSendTruckLoadRequest | purchase_auto_order_send_truck_load_request | purchase/migrations/0030_purchaseautoordersendtruckloadrequest.py:23 |
| PurchaseActualKikanMapping | purchase_actual_kikan_mapping | purchase/migrations/0021_purchase_actual_kikan_mapping.py:39 |

参考: `purchase_order_approval_config`(PurchaseOrderApprovalConfig)は0007作成後、0037で削除済み。対応不要。

### quality(30モデル、TrainingOrgSnapshotMixinは抽象のため除外)

| モデル | db_table | 作成migration |
|---|---|---|
| EquipmentInspectionTemplate | quality_equipment_inspection_template | quality/migrations/0006_equipmentinspectiontemplate_equipmentinspectionitem_and_more.py:43 |
| EquipmentInspectionItem | quality_equipment_inspection_item | quality/migrations/0006...py:70 |
| EquipmentInspectionItemAttachment | quality_equipment_inspection_item_attachment | quality/migrations/0008_equipmentinspectionrecord_equipmentinspectionresult_and_more.py:115 |
| EquipmentInspectionRecord | quality_equipment_inspection_record | quality/migrations/0008...py:38 |
| EquipmentInspectionResult | quality_equipment_inspection_result | quality/migrations/0008...py:69 |
| EquipmentInspectionConfirmation | quality_equipment_inspection_confirmation | quality/migrations/0008...py:91 |
| EquipmentInspectionTask | quality_equipment_inspection_task | quality/migrations/0009_equipmentinspectiontemplate_chief_reviewed_at_and_more.py:136 |
| EquipmentInspectionWorkflowLog | quality_equipment_inspection_workflow_log | quality/migrations/0006...py:89 |
| IntegratedChecksheetTemplate | quality_integrated_checksheet_template | quality/migrations/0019_integrated_checksheet.py:31 |
| IntegratedChecksheetProcessBlock | quality_integrated_cs_process_block | quality/migrations/0019...py:48 |
| IntegratedChecksheetItem | quality_integrated_cs_item | quality/migrations/0019...py:71 |
| IntegratedChecksheetItemAttachment | quality_integrated_cs_item_attachment | quality/migrations/0034_integrated_checksheet_item_remarks_attachment.py:37 |
| IntegratedChecksheetSketchField | quality_integrated_cs_sketch_field | quality/migrations/0019...py:157 |
| IntegratedChecksheetBatch | quality_integrated_checksheet_batch | quality/migrations/0019...py:93 |
| IntegratedChecksheetUnit | quality_integrated_checksheet_unit | quality/migrations/0019...py:115 |
| IntegratedChecksheetCheck | quality_integrated_cs_check | quality/migrations/0019...py:135 |
| IntegratedChecksheetSketchResponse | quality_integrated_cs_sketch_response | quality/migrations/0019...py:176 |
| IntegratedChecksheetTask | quality_integrated_cs_task | quality/migrations/0026_add_integrated_checksheet_task.py:36 |
| IntegratedChecksheetWorkflowLog | quality_integrated_cs_workflow_log | quality/migrations/0027_add_workflow_log_and_dates_to_integrated_checksheet.py:46 |
| ChecksheetReworkAlertConfig | quality_checksheet_rework_alert_config | quality/migrations/0041_checksheetreworkalertconfig.py:37 |
| ScrapRecord | t_scrap_record | orders/migrations/0021_scraprecord.py:13-32(実DDL、§2-2参照) |
| ScrapRecordDetail | t_scrap_record_detail | orders/migrations/0024_scraprecorddetail.py:13-33(実DDL、§2-2参照) |
| TrainingBook | quality_training_book | quality/migrations/0037_trainingbook_trainingexamdefinition_and_more.py:35 |
| TrainingQuestion | quality_training_question | quality/migrations/0037...py:153 |
| TrainingExamDefinition | quality_training_exam_definition | quality/migrations/0037...py:57 |
| TrainingExamQuestion | quality_training_exam_question | quality/migrations/0037...py:168 |
| TrainingTrack | quality_training_track | quality/migrations/0037...py:188 |
| TrainingExamSession | quality_training_exam_session | quality/migrations/0037...py:87 |
| TrainingExamAttempt | quality_training_exam_attempt | quality/migrations/0037...py:123 |
| TrainingStepRecord | quality_training_step_record | quality/migrations/0037...py:214 |

参考: `quality_product_checksheet_*`系(0014作成)は0039で削除済み。対応不要。

### shifts(4モデル、db_table未指定=既定命名)

| モデル | db_table | 作成migration |
|---|---|---|
| ShiftLine | shifts_shiftline | shifts/migrations/0001_initial.py:16-17 |
| ShiftWorker | shifts_shiftworker | shifts/migrations/0001_initial.py:31-32 |
| ShiftLineProcess | shifts_shiftlineprocess | shifts/migrations/0001_initial.py:71-72 |
| ShiftAssignment | shifts_shiftassignment | shifts/migrations/0001_initial.py:50-51 |

### shipping(10モデル、★=§2-1の重複対象)

| モデル | db_table | 作成migration |
|---|---|---|
| ShipmentActual★ | t_shipment_actual | shipping/migrations/0001_initial.py:17-35 |
| ShipmentActualSplit | t_shipment_actual_split | shipping/migrations/0005_shipmentactualsplit.py:27 |
| ShippingTripAllocationSplit | t_shipping_trip_allocation_split | shipping/migrations/0007_shippingtripallocationsplit.py:30 |
| ShipmentActualHistory★ | t_shipment_actual_history | shipping/migrations/0001_initial.py:38-55 |
| ShipToLeadTime | m_ship_to_lead_time | shipping/migrations/0001_initial.py:73 |
| ShipToLeadTimeColorExclusion | m_ship_to_lead_time_color_exclusion | shipping/migrations/0011_shiptoleadtimecolorexclusion.py:22 |
| DeliveryProgress★ | t_delivery_progress | shipping/migrations/0001_initial.py:77-93 |
| KubotaSakaiDeliveryProgress | t_kubota_sakai_delivery_progress | shipping/migrations/0003_kubota_sakai_delivery_progress.py:30 |
| ShippingProgress | t_shipping_progress | shipping/migrations/0008_shippingprogress.py:32 |
| KubotaSakaiTripDisplaySetting | t_kubota_sakai_trip_display_setting | shipping/migrations/0004_kubotasakaitripdisplaysetting.py:26 |

### system_settings(1モデル)

| モデル | db_table | 作成migration |
|---|---|---|
| SystemSetting | system_settings | system_settings/migrations/0001_initial.py:34 |

---

## 4. RunSQL/ビュー移植ワークリスト(38件全件)

| file:line | 種類 | 対象オブジェクト | PG書き換え要否 |
|---|---|---|---|
| ai/migrations/0012_ai_purchase_receipt_view.py:39 | CREATE OR REPLACE VIEW | v_ai_purchase_receipt | **要**(`JSON_VALUE(...RETURNING DATE/UNSIGNED)`。開発者コメントで`->>`演算子への書き換えを明記済み) |
| ai/migrations/0013_ai_purchase_receipt_view_record_type.py:43 | CREATE OR REPLACE VIEW | v_ai_purchase_receipt | **要**(同上。0012の後継版) |
| ai/migrations/0014_ai_shipment_view.py:35 | CREATE OR REPLACE VIEW | v_ai_shipment | 不要 |
| ai/migrations/0034_ai_product_view.py:57 | CREATE OR REPLACE VIEW | v_ai_product(32列) | 不要 |
| ai/migrations/0035_ai_process_view.py:35 | CREATE OR REPLACE VIEW | v_ai_process | 不要 |
| ai/migrations/0036_ai_line_view.py:32 | CREATE OR REPLACE VIEW | v_ai_line | 不要 |
| ai/migrations/0037_ai_product_view_remove_dates.py:92 | CREATE OR REPLACE VIEW | v_ai_product(30列) | 不要 |
| ai/migrations/0038_ai_supplier_view.py:31 | CREATE OR REPLACE VIEW | v_ai_supplier | 不要 |
| ai/migrations/0039_ai_customer_view.py:32 | CREATE OR REPLACE VIEW | v_ai_customer | 不要 |
| ai/migrations/0040_ai_calendar_day_view.py:42 | CREATE OR REPLACE VIEW | v_ai_calendar_day | 不要 |
| ai/migrations/0041_ai_bom_item_view.py:68 | CREATE OR REPLACE VIEW | v_ai_bom_item | 不要 |
| ai/migrations/0042_ai_routing_step_view.py:73 | CREATE OR REPLACE VIEW | v_ai_routing_step | 不要 |
| ai/migrations/0043_ai_routing_step_material_view.py:58 | CREATE OR REPLACE VIEW | v_ai_routing_step_material | 不要 |
| ai/migrations/0045_ai_user_view.py:60 | CREATE OR REPLACE VIEW | v_ai_user | 不要 |
| ai/migrations/0046_ai_department_view.py:31 | CREATE OR REPLACE VIEW | v_ai_department | 不要 |
| ai/migrations/0048_ai_unit_line_view.py:37 | CREATE OR REPLACE VIEW | v_ai_unit_line | 不要 |
| ai/migrations/0049_ai_supervisor_team_view.py:39 | CREATE OR REPLACE VIEW | v_ai_supervisor_team | 不要 |
| ai/migrations/0050_ai_leader_unit_view.py:39 | CREATE OR REPLACE VIEW | v_ai_leader_unit | 不要 |
| ai/migrations/0051_routing_parent_product_views.py:87 | CREATE OR REPLACE VIEW | v_ai_routing_step | 不要 |
| ai/migrations/0051_routing_parent_product_views.py:88 | CREATE OR REPLACE VIEW | v_ai_routing_step_material | 不要 |
| ai/migrations/0054_ai_equipment_view.py:30 | CREATE OR REPLACE VIEW | v_ai_equipment | 不要 |
| ai/migrations/0055_ai_process_production_actual_view.py:44 | CREATE OR REPLACE VIEW | v_ai_process_production_actual | **要**(`DATE(timestamp - INTERVAL 8 HOUR)`。PGは`INTERVAL '8 hours'`形式。開発者コメントに注記済み) |
| ai/migrations/0056_ai_laser_production_actual_view.py:62 | CREATE OR REPLACE VIEW | v_ai_laser_production_actual | 不要 |
| ai/migrations/0057_ai_brake_production_actual_view.py:40 | CREATE OR REPLACE VIEW | v_ai_brake_production_actual | 不要 |
| ai/migrations/0058_ai_laser_interruption_view.py:46 | CREATE OR REPLACE VIEW | v_ai_laser_interruption | 不要 |
| ai/migrations/0059_ai_brake_production_actual_view_add_columns.py:60 | CREATE OR REPLACE VIEW | v_ai_brake_production_actual | 不要 |
| ai/migrations/0060_ai_brake_interruption_view.py:41 | CREATE OR REPLACE VIEW | v_ai_brake_interruption | 不要 |
| ai/migrations/0061_ai_process_interruption_view.py:54 | CREATE OR REPLACE VIEW | v_ai_process_interruption | **要**(`JSON_UNQUOTE(JSON_EXTRACT(...))`。開発者コメントに書き換え必要と明記済み) |
| ai/migrations/0062_ai_laser_views_add_interruption_reason_code.py:147 | CREATE OR REPLACE VIEW | v_ai_laser_production_actual | 不要 |
| ai/migrations/0062_ai_laser_views_add_interruption_reason_code.py:148 | CREATE OR REPLACE VIEW | v_ai_laser_interruption | 不要 |
| quality/migrations/0002_add_is_production_recorded.py:13 | ALTER TABLE(列追加) | t_scrap_record | **要**(`TINYINT(1)`→`BOOLEAN`) |
| quality/migrations/0003_add_is_backlog_processed.py:13 | ALTER TABLE(列追加) | t_scrap_record_detail | **要**(同上) |
| quality/migrations/0003_add_is_backlog_processed.py:18 | データ更新(UPDATE) | t_scrap_record_detail | 不要 |
| quality/migrations/0004_add_occurrence_process_to_scraprecord.py:11 | ALTER TABLE(列追加) | t_scrap_record | 不要 |
| quality/migrations/0004_add_occurrence_process_to_scraprecord.py:15 | ALTER TABLE(FK制約追加) | t_scrap_record→m_process | **要**(reverse_sqlの`DROP FOREIGN KEY`→`DROP CONSTRAINT`) |
| quality/migrations/0039_drop_product_checksheet_tables.py:13 | DROP TABLE(IF EXISTS、7テーブル) | quality_product_checksheet_* | 不要 |
| orders/migrations/0050_rebuild_kubota_sakai_due_adjustment.py:19 | データ削除(DELETE) | t_kubota_sakai_due_adjustment | 不要 |
| masters/migrations/0009_drop_legacy_routing_step_output.py:14 | DROP TABLE(IF EXISTS) | m_routing_step_output | 不要(reverse_sqlが空文字である点は別途要確認) |

**集計**: 38件中、書き換え必要7件(JSON系4件・TINYINT(1)系2件・DROP FOREIGN KEY系1件)、不要31件。DEFINER句を使うビューは0件(マイグレーション内では)。`pm_ai_view_owner`はマイグレーション本体には出現せず、別の管理コマンド(`setup_ai_views`等)側にあると推測されるが本調査のスコープ外(未確認)。

---

## 5. 型・制約変換表(優先度別)

| 優先度 | 項目 | 内容 | 該当箇所 |
|---|---|---|---|
| 高 | 動的SQLのバッククォート識別子 | `analysis_data_service.py:585,588,604`でバッククォートによる識別子クォートを使用。PGは二重引用符が必要なため書き換え必須 | `apps/ai/services/analysis_data_service.py` |
| 高 | AIビューのJSON抽出・INTERVAL書式 | §4の7件(JSON_VALUE/JSON_EXTRACT/JSON_UNQUOTE4件、INTERVAL数値リテラル1件、TINYINT(1)2件) | §4参照 |
| 高 | PG接続時のセッションtimezone設定 | `USE_TZ=False`・`TIME_ZONE='Asia/Tokyo'`(settings.py)。MySQLは`init_command`でセッションtime_zoneを'+09:00'固定しているが、PGには同等の仕組みが無く、接続時に`SET TIME ZONE 'Asia/Tokyo'`または`DATABASES['OPTIONS']['options']`で明示設定が必要。怠るとNOW()等のSQL関数結果がUTC基準にずれるリスク | `project/settings.py:199,203,129,156` |
| 中 | CharField(unique=True)の大文字小文字 | 約45件(主にmasters、例: product_code/customer_code/line_code)。db_collationの明示指定は無し。MySQLのデフォルト照合(大文字小文字非区別が多い)からPG(区別)への移行で、既存データに大小文字違いの隠れ重複が無いか事前データ検証が必要 | `apps/masters/models.py`他 |
| 中 | JSONField(raw_payload系) | 58件。キー順・空白はMySQL/PGとも内部正規化されるため値比較上は概ね問題ないが、「生データをそのまま文字列として再利用する」用途(`raw_payload`等)は再現性の変化に注意 | `apps/ai/models.py:148`、`apps/orders/core/models.py:494`等 |
| 低 | BigAutoFieldのシーケンス採番 | 全モデルで`BigAutoField`明示指定(100件超)。方式Qでデータ移行後、PG側のシーケンス現在値をMySQLのAUTO_INCREMENT値に合わせて`setval()`し直す手順が必要 | 全アプリ共通 |
| 低 | DecimalField | 約85件、精度・丸め規則はMySQL/PGで実質同一(四捨五入) | 例: `apps/shipping/models.py:26` |
| 低 | BooleanField(null許容) | 160件使用中、`null=True`は2件のみ(`apps/masters/models.py:800-801` can_mix/stackable)。この2件のみ要確認、他はNOT NULLで安全 | `apps/masters/models.py` |
| 低 | unique_together/UniqueConstraint | 約85件、prefix index・FULLTEXT等MySQL固有機能の使用なし。標準機能のみでPG互換性問題なし | 各アプリ |
| 低 | db_table未指定(デフォルト命名)の8モデル | masters(MobileDevice系3・ManualDocument)、shifts(4件)。方式Qで実スキーマをそのまま使う場合、実DB側も本当にデフォルト名(`masters_mobiledevice`等)になっているか確認要 | §3参照 |
| - | GROUP_CONCAT/DATE_ADD/STR_TO_DATE/CAST(...AS SIGNED)/ENUM/SET/YEAR/MEDIUMTEXT/UNSIGNED/FULLTEXT | リポジトリ全体(models/migrations/services)で**使用箇所なし** | - |

---

## 6. 対応方針(提案、未承認)

1. **db_table重複(12件)**: **2026-10-20 実施・検証済み**。`D:\pm_pg`で、quality/aiと同じ`SeparateDatabaseAndState`パターンでproduction 9件・shipping 3件を包んだ(generator実装・evaluator検証合格)。さらに実機`migrate`試験で、`production/migrations/0001_initial.py`に`orders`アプリへの依存が無かったため実行順序が崩れる問題が判明し、`dependencies`に`('orders', '0029_linebacklog_plan_id')`を追加して解消(詳細は`仕様書/PostgreSQL移行計画書_v3.md`§3-2参照)。空PG(`pm-pg-rehearsal`)への`migrate`で、production・masters・notifications・quality.0001_initialまで正常適用を実機確認済み
2. **AIビュー4件の書き換え**: `->>`演算子・`::`キャスト・`INTERVAL '8 hours'`形式への書き換え。対象ビューのSQL本体のみの変更で、呼び出し元のAPIには影響しない想定(要検証、未着手)
3. **動的SQL(analysis_data_service.py)**: バッククォート→二重引用符。PG接続時に分岐が必要(フォールバック実装の制限に注意、CLAUDE.md規約により事前同意が必要、未着手)
4. **TINYINT(1)・DROP FOREIGN KEY(3件)**: ALTER TABLE文の書き換え。**2026-10-20 実機確認**: `quality.0002_add_is_production_recorded`の`TINYINT(1)`が実際にPGで`type "tinyint" does not exist`エラーになることを確認した(未着手、次の対応候補)
5. **PG接続のセッションtimezone設定**: 新規の接続設定追加(DATABASES['OPTIONS']等、未着手)
6. **シーケンス調整**: データ投入後、`setval()`で全テーブルのシーケンスをMySQLのAUTO_INCREMENT値に合わせる手順をQ実行手順書に明記(未着手)
7. **db_table未指定8モデル**: 実DBでの命名を事前確認(未着手)

1以外はいずれも**実施はBOSS承認後**。本書は調査結果の整理のみ。

---

## 7. 未確定事項・BOSSへの確認事項

- RunSQL件数の「29箇所/26ファイル」(旧稿記載)と今回の実測「38箇所/34ファイル」の差異原因は未調査(集計条件の違いと推測されるが未確定)
- `masters/migrations/0009_drop_legacy_routing_step_output.py`のreverse_sqlが空文字("")である点の挙動(意図的かどうか)は未確認

### `pm_ai_view_owner`の調査結果(2026-10-20、解消)

実体は`pm_backend/apps/ai/management/commands/setup_ai_views.py`。

- **MySQL専用**(`connection.vendor != 'mysql'`なら何もしない設計。コード内コメント「PostgreSQL版は、移行時に作る」)。PG移行時はこのコマンド自体の書き直しが必要
- 対象は2系統:
  1. 単純なマスタビュー7件(`v_ai_product`等)→コマンドが`CREATE OR REPLACE DEFINER = pm_ai_view_owner ... SQL SECURITY DEFINER VIEW`を自動生成・適用(`--apply`)
  2. 結合・WHERE句を含むビュー17件(migrations 0012-0014・0040-0043・0045・0046・0048-0050・0055・0056・0058・0060・0061)→コマンドは`--check`での確認のみ。定義者の付け替えは手動SQL(`scripts/repair_routing_ai_view_definers.sql.txt`等)をBOSSが本番Adminerで実行
- 読者アカウント名は`pm_ai_reader`(コード内`READER_USER`定数)
- **PG移行での注意点**: PGにはMySQLの`DEFINER`/`SQL SECURITY DEFINER`に相当する概念が無く、PGはビューの**所有者(OWNER)**がデフォルトで実行権限を持つ設計。単純な構文置換では済まず、GRANT/REVOKEの設計自体をPG用に作り直す必要がある(§3-4にも追記済み)
