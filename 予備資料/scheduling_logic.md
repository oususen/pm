# スケジューリング逆算ロジック（擬似コード）

## 前提
- 受注：(product=P_FINAL, qty=Q, due_date=DUE)
- ルーティング：上位の3工程は日単位（lead_time_days）、溶接配下は分単位（duration_min または算出）
- カレンダ：m_calendar_day(work_minutes, is_working_day)

## 関数
- work_back(date, minutes): その日の稼働分を消費しながら minutes だけ過去に遡る
- work_forward(date, minutes): 未来へ進める
- calc_duration(product, process, line, qty):
    ct = m_cycle_time.lookup(product, process, line)
    return ct.setup_time_min*60 + ct.cycle_time_sec*qty

## 手順（完成品のDUEから逆算）
1) FINALのルーティングを取得（step_no降順）
2) for step in steps_desc:
      if step.is_day_level:       # lead_time_days > 0 or duration_min is null and day planning
          start = shift_business_days(end, -step.lead_time_days, calendar)
      else:                       # minute-level
          qty = lot_size or order_qty
          dur = step.duration_min or calc_duration(product_of_step, process, line, qty)
          start = work_back(end, dur)  # calendar.work_minutes 使用
      if has_transfer_batch(step):
          # 前工程から transfer_batch_qty ごとに着手できるので、
          # 実際の start は predecessor の最初のバッチ完成時刻を使用
          start = max(start, predecessor.first_batch_finish_time)
      end = start

3) 先頭ステップのstartがオーダの開始時刻
4) 購買品は投入予定日から purchase_lt_days で発注日を逆算

## 逐次着手（移送バッチ）
- predecessor 完了数量が transfer_batch_qty に到達するたびに
  successor を起動し、time-window(daily_time_window_min) 内で割り付ける。
- バッファは target_buffer_qty〜max_buffer_qty を維持するよう前工程速度をスロットリング。
