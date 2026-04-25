import Image from "next/image";

export type StoreItem = {
  id: string;
  name: string;
  imageUrl: string;
  latitude: number;
  longitude: number;
};

type StoreCardProps = {
  item: StoreItem;
};

export default function StoreCard({ item }: StoreCardProps) {
  return (
    <article className="rounded-2xl border border-zinc-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-zinc-100">
        <Image
          src={item.imageUrl}
          alt={item.name}
          fill
          className="object-cover"
          sizes="(max-width: 640px) 90vw, (max-width: 1024px) 40vw, 22vw"
        />
      </div>
      <p className="pt-3 text-center text-sm font-medium text-zinc-800">{item.name}</p>
    </article>
  );
}
