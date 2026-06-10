import React, { useState } from "react";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function CalendarView({ entries, selectedDate, onSelectDate }) {
  const [currentMonth, setCurrentMonth] = useState(() => new Date());

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const todayStr = new Date().toISOString().split("T")[0];

  const entryMap = {};
  for (const e of entries) {
    const d = e.date || "";
    if (!entryMap[d]) entryMap[d] = [];
    entryMap[d].push(e);
  }

  function dayHours(d) {
    const dayEntries = entryMap[d] || [];
    let total = 0;
    for (const e of dayEntries) {
      if (e.activity_type === "other") {
        total += e.activity_time || 0;
      } else if (e.activity_type === "leave_travel") {
        total += e.time || 0;
      } else {
        total += (e.work_time || 0) + (e.reviewer_time || 0);
      }
    }
    return total;
  }

  function fmtHours(hours) {
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}:${String(m).padStart(2, "0")}`;
  }

  function pad(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function dateStr(day) {
    return `${year}-${pad(month + 1)}-${pad(day)}`;
  }

  function prevMonth() {
    setCurrentMonth(new Date(year, month - 1, 1));
  }

  function nextMonth() {
    setCurrentMonth(new Date(year, month + 1, 1));
  }

  const cells = [];
  for (let i = 0; i < firstDay; i++) {
    cells.push(<div key={`empty-${i}`} className="cal-day cal-empty" />);
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const ds = dateStr(day);
    const hours = dayHours(ds);
    const hasEntries = hours > 0;
    const isSelected = ds === selectedDate;
    const isToday = ds === todayStr;
    let cls = "cal-day";
    if (hasEntries) cls += " cal-has-entries";
    if (isSelected) cls += " cal-selected";
    if (isToday) cls += " cal-today";
    cells.push(
      <div key={ds} className={cls} onClick={() => onSelectDate(ds)}>
        <span className="cal-day-num">{day}</span>
        {hasEntries && <span className="cal-day-hours">{fmtHours(hours)}h</span>}
      </div>
    );
  }

  return (
    <div className="calendar">
      <div className="cal-header">
        <button className="cal-nav" onClick={prevMonth}>&lt;</button>
        <span className="cal-title">{MONTHS[month]} {year}</span>
        <button className="cal-nav" onClick={nextMonth}>&gt;</button>
      </div>
      <div className="cal-weekdays">
        {DAYS.map(d => <div key={d} className="cal-weekday">{d}</div>)}
      </div>
      <div className="cal-grid">
        {cells}
      </div>
    </div>
  );
}
