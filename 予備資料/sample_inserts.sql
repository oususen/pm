-- sample_inserts.sql  段階BOM・ルーティング・能力・パラメータのサンプル

-- Products (final & WIP tiers)
INSERT INTO m_product(product_code, product_name, category, unit, is_final_product) VALUES
('P_FINAL','完成品A','集合','個',1),
('P_OUTFIT','艤装段階','集合','個',0),
('P_AIR','気密段階','集合','個',0),
('P_COMP','コンプ段階','集合','個',0),
('P_SUB2','サブ2','集合','個',0),
('P_SUB1','サブ1','集合','個',0);

-- Processes
INSERT INTO m_process(process_code, process_name) VALUES
('LASER','レーザ切断'),
('BEND','ブレーキ曲げ'),
('SPOT','プロジェクションSpot'),
('WELD','溶接');

-- Lines
INSERT INTO m_line(line_code, line_name) VALUES
('LINE_LASER','レーザライン'),
('LINE_PRESS','プレスライン'),
('LINE_SPOT','スポットライン'),
('LINE_WELD','溶接ライン');

-- Optional line default LT (days)
INSERT INTO m_line_default(line_id, default_lt_days)
SELECT id, 1 FROM m_line WHERE line_code IN ('LINE_LASER','LINE_PRESS','LINE_SPOT');

-- Routing header (default)
INSERT INTO m_routing(product_id, routing_code, is_default)
SELECT id, 'std', 1 FROM m_product WHERE product_code='P_FINAL';

-- Get routing id
-- (Note: in real env, use SELECT ...)
SET @RID = (SELECT r.id FROM m_routing r JOIN m_product p ON p.id=r.product_id AND p.product_code='P_FINAL' LIMIT 1);
SET @PROC_LASER = (SELECT id FROM m_process WHERE process_code='LASER');
SET @PROC_BEND  = (SELECT id FROM m_process WHERE process_code='BEND');
SET @PROC_SPOT  = (SELECT id FROM m_process WHERE process_code='SPOT');
SET @PROC_WELD  = (SELECT id FROM m_process WHERE process_code='WELD');
SET @LINE_LASER = (SELECT id FROM m_line WHERE line_code='LINE_LASER');
SET @LINE_PRESS = (SELECT id FROM m_line WHERE line_code='LINE_PRESS');
SET @LINE_SPOT  = (SELECT id FROM m_line WHERE line_code='LINE_SPOT');
SET @LINE_WELD  = (SELECT id FROM m_line WHERE line_code='LINE_WELD');

-- Routing steps (day-level for top 3, minute-level for weld chain)
INSERT INTO m_routing_step(routing_id, step_no, process_id, line_id, lead_time_days, remark)
VALUES
(@RID,1,@PROC_LASER,@LINE_LASER,1,'日扱い'),
(@RID,2,@PROC_BEND ,@LINE_PRESS,1,'日扱い'),
(@RID,3,@PROC_SPOT ,@LINE_SPOT ,1,'日扱い');

-- Weld chain as minute-level steps (5 stations, 240 min time-window each as param)
INSERT INTO m_routing_step(routing_id, step_no, process_id, line_id, start_offset_min, duration_min, remark)
VALUES
(@RID,41,@PROC_WELD,@LINE_WELD,0,NULL,'サブ1'),
(@RID,42,@PROC_WELD,@LINE_WELD,0,NULL,'サブ2'),
(@RID,43,@PROC_WELD,@LINE_WELD,0,NULL,'コンプ'),
(@RID,44,@PROC_WELD,@LINE_WELD,0,NULL,'気密'),
(@RID,45,@PROC_WELD,@LINE_WELD,0,NULL,'艤装');

-- Step outputs (what product becomes available at each station)
SET @P_SUB1   = (SELECT id FROM m_product WHERE product_code='P_SUB1');
SET @P_SUB2   = (SELECT id FROM m_product WHERE product_code='P_SUB2');
SET @P_COMP   = (SELECT id FROM m_product WHERE product_code='P_COMP');
SET @P_AIR    = (SELECT id FROM m_product WHERE product_code='P_AIR');
SET @P_OUTFIT = (SELECT id FROM m_product WHERE product_code='P_OUTFIT');

INSERT INTO m_routing_step_output(routing_step_id, output_product_id, is_final_stage)
VALUES
((SELECT id FROM m_routing_step WHERE routing_id=@RID AND step_no=41), @P_SUB1, 0),
((SELECT id FROM m_routing_step WHERE routing_id=@RID AND step_no=42), @P_SUB2, 0),
((SELECT id FROM m_routing_step WHERE routing_id=@RID AND step_no=43), @P_COMP, 0),
((SELECT id FROM m_routing_step WHERE routing_id=@RID AND step_no=44), @P_AIR,  0),
((SELECT id FROM m_routing_step WHERE routing_id=@RID AND step_no=45), @P_OUTFIT, 1);

-- Step params: lot=40, transfer batch=4, daily time-window=240min
INSERT INTO m_routing_step_param(routing_step_id, lot_size, transfer_batch_qty, start_trigger, target_buffer_qty, max_buffer_qty, daily_time_window_min)
SELECT id, 40, 4, 'on_transfer_batch', 8, 20, 240
FROM m_routing_step WHERE routing_id=@RID AND step_no BETWEEN 41 AND 45;

-- Cycle times (examples; seconds per unit + setup)
INSERT INTO m_cycle_time(product_id, process_id, line_id, cycle_time_sec, setup_time_min, valid_from)
VALUES
(@P_SUB1 , @PROC_WELD, @LINE_WELD, 30, 10, CURRENT_DATE()),
(@P_SUB2 , @PROC_WELD, @LINE_WELD, 40, 10, CURRENT_DATE()),
(@P_COMP , @PROC_WELD, @LINE_WELD, 35, 10, CURRENT_DATE()),
(@P_AIR  , @PROC_WELD, @LINE_WELD, 80,  5, CURRENT_DATE()),
(@P_OUTFIT, @PROC_WELD, @LINE_WELD, 90,  0, CURRENT_DATE());

-- BOM (staged): FINAL -> OUTFIT -> AIR -> COMP -> SUB2 -> SUB1
INSERT INTO m_bom(parent_product_id, version, valid_from)
SELECT id, 'v1', CURRENT_DATE() FROM m_product WHERE product_code IN ('P_FINAL','P_OUTFIT','P_AIR','P_COMP','P_SUB2');

SET @BOM_FINAL  = (SELECT id FROM m_bom b JOIN m_product p ON p.id=b.parent_product_id AND p.product_code='P_FINAL' LIMIT 1);
SET @BOM_OUTFIT = (SELECT id FROM m_bom b JOIN m_product p ON p.id=b.parent_product_id AND p.product_code='P_OUTFIT' LIMIT 1);
SET @BOM_AIR    = (SELECT id FROM m_bom b JOIN m_product p ON p.id=b.parent_product_id AND p.product_code='P_AIR' LIMIT 1);
SET @BOM_COMP   = (SELECT id FROM m_bom b JOIN m_product p ON p.id=b.parent_product_id AND p.product_code='P_COMP' LIMIT 1);
SET @BOM_SUB2   = (SELECT id FROM m_bom b JOIN m_product p ON p.id=b.parent_product_id AND p.product_code='P_SUB2' LIMIT 1);

INSERT INTO m_bom_item(bom_id, child_product_id, quantity) VALUES
(@BOM_FINAL , @P_OUTFIT, 1),
(@BOM_OUTFIT, @P_AIR   , 1),
(@BOM_AIR   , @P_COMP  , 1),
(@BOM_COMP  , @P_SUB2  , 1),
(@BOM_SUB2  , @P_SUB1  , 1);
