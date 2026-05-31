import StorebookPage from "@/components/StorebookPage";

type HomeProps = {
  searchParams: Promise<{ uuid?: string | string[] }>;
};

function parseUuidFromSearchParams(
  rawUuid: string | string[] | undefined,
): string | undefined {
  const value = Array.isArray(rawUuid) ? rawUuid[0] : rawUuid;
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const bookmarksUuidFromUrl = parseUuidFromSearchParams(params.uuid);

  return <StorebookPage bookmarksUuidFromUrl={bookmarksUuidFromUrl} />;
}
