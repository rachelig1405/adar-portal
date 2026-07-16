export default function Logo({ className = "" }) {
  return <img src="/logo.png" onError={(e)=>{e.currentTarget.src="/logo.svg"}} className={className} alt="ADAR Toys & More" />;
}
