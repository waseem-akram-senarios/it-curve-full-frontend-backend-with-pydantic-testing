<!--BEGIN_BANNER_IMAGE-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/.github/banner_dark.png">
  <source media="(prefers-color-scheme: light)" srcset="/.github/banner_light.png">
  <img style="width:100%;" alt="Repository banner image with sample code in the background." src="/.github/banner_light.png">
</picture>

<!--END_BANNER_IMAGE-->

# Virtual Agent Playground

<!--BEGIN_DESCRIPTION-->
The Virtual Agent Playground is designed for quickly prototyping with server side agents. Easily process or generate audio, video, and data streams. The playground includes components to fully interact with any virtual agent through video, audio and chat.
<!--END_DESCRIPTION-->

## Available Pages

- **Chat Widget**: Embeddable chat widget that can be included in other websites

## Setting up the playground locally

1. Install dependencies

```bash
  npm install
```

2. Copy and rename the `.env.example` file to `.env.local` and fill in the necessary environment variables.

```
LIVEKIT_API_KEY=<your API KEY>
LIVEKIT_API_SECRET=<Your API Secret>
NEXT_PUBLIC_LIVEKIT_URL=wss://<Your Cloud URL>
```

3. Run the development server:

```bash
  npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.
5. If you haven't done so yet, start your agent (with the same project variables as in step 2.)
6. Connect to a room and see your agent connecting to the playground

## Features

- Render video, audio and chat from your agent
- Send video, audio, or text to your agent
- Configurable settings panel to work with your agent
- Embeddable chat widget for integration into other websites




