import { LINKS } from "./links";
const warehouse = [
  { key:"startPicking", title:"תחילת ליקוט", subtitle:"פתיחת תהליך ליקוט להזמנה", icon:"🟢", color:"green", url:LINKS.startPicking },
  { key:"endPicking", title:"סיום ליקוט", subtitle:"עדכון סיום ליקוט", icon:"✅", color:"blue", url:LINKS.endPicking },
  {key:"check", title:"בדיקת הזמנה", subtitle:"עדכון בדיקת הזמנה", icon:"✅", color:"green", url:LINKS.check},
  { key:"loading", title:"העמסה", subtitle:"עדכון העמסת הזמנה", icon:"🚚", color:"pink", url:LINKS.loading },
  { key:"orders", title:"כל ההזמנות", subtitle:"תצוגת הזמנות מהמערכת", icon:"📦", color:"yellow", url:LINKS.allOrders },
  { key:"dashboard", title:"דשבורד מחסן", subtitle:"נתוני מחסן וסטטוסים", icon:"📊", color:"purple", url:LINKS.warehouseDashboard},
 

];
const office = [
  { key:"newCustomer", title:"לקוח חדש", subtitle:"פתיחת לקוח חדש", icon:"👤", color:"green", url:LINKS.newCustomer },
  { key:"newOrder", title:"קליטת הזמנה", subtitle:"יצירת הזמנה חדשה", icon:"🧾", color:"blue", url:LINKS.newOrder },
  { key:"customers", title:"לקוחות", subtitle:"ממשק לקוחות", icon:"👥", color:"pink", url:LINKS.customers },
  { key:"orders", title:"הזמנות", subtitle:"כל ההזמנות במערכת", icon:"📋", color:"yellow", url:LINKS.allOrders },
  { key:"dashboard", title:"דשבורד משרד", subtitle:"תצוגת ניהול משרד", icon:"📊", color:"purple", url:LINKS.officeDashboard },
  {
    key: "importOrdersExcel",
    title: "קליטת הזמנות מאקסל",
    subtitle: "העלאת קובץ הזמנות",
    icon: "📊",
   color: "green",
  }
];
const admin=[
    { key:"newCustomer", title:"לקוח חדש", subtitle:"פתיחת לקוח חדש", icon:"👤", color:"green", url:LINKS.newCustomer },
  { key:"newOrder", title:"קליטת הזמנה", subtitle:"יצירת הזמנה חדשה", icon:"🧾", color:"blue", url:LINKS.newOrder },
  { key:"customers", title:"לקוחות", subtitle:"ממשק לקוחות", icon:"👥", color:"pink", url:LINKS.customers },
  { key:"orders", title:"הזמנות", subtitle:"כל ההזמנות במערכת", icon:"📋", color:"yellow", url:LINKS.allOrders },
  { key:"dashboard", title:"דשבורד משרד", subtitle:"תצוגת ניהול משרד", icon:"📊", color:"purple", url:LINKS.officeDashboard },
  {
    key: "importOrdersExcel",
    title: "קליטת הזמנות מאקסל",
    subtitle: "העלאת קובץ הזמנות",
    icon: "📊",
   color: "green",
  },
   { key:"startPicking", title:"תחילת ליקוט", subtitle:"פתיחת תהליך ליקוט להזמנה", icon:"🟢", color:"green", url:LINKS.startPicking },
  { key:"endPicking", title:"סיום ליקוט", subtitle:"עדכון סיום ליקוט", icon:"✅", color:"blue", url:LINKS.endPicking },
  {key:"check", title:"בדיקת הזמנה", subtitle:"עדכון בדיקת הזמנה", icon:"✅", color:"green", url:LINKS.check},
  { key:"loading", title:"העמסה", subtitle:"עדכון העמסת הזמנה", icon:"🚚", color:"pink", url:LINKS.loading },
  {key:"stickers",title:"יצירת סטיקרים",subtitle:"", icon: "📄",color:"yellow"}
];
export function getMenu(role) {
  if (role === "warehouse") return warehouse;
  if (role === "office") return office;
  if (role === "admin") return admin;
  return [...office, ...warehouse.filter(w => !office.find(o => o.key === w.key))];
}
