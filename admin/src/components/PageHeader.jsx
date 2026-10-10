export default function PageHeader({ title, titleId, before, meta, aside }) {
  return (
    <>
      {before}
      <header className="page-header">
        <div className="page-header-main">
          <h1 id={titleId}>{title}</h1>
          {meta}
        </div>
        {aside && <div className="page-header-aside">{aside}</div>}
      </header>
    </>
  );
}
