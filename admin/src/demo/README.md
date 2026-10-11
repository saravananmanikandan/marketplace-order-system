# Demo tools

Demo-only tools, not part of the assignment requirements. Delete this folder and the one import in the top bar to remove them.

- `DemoLauncher.jsx` asks `GET /demo/api/config` once and renders nothing when the demo app is off or unreachable.
- `SimulatorDrawer.jsx` sends simulated Uber Eats and DoorDash webhooks through `POST /demo/api/send` and shows what came back.
- `demoApi.js` holds the three requests; `demo.css` holds the drawer styles and reuses the design tokens from `styles/tokens.css`.
