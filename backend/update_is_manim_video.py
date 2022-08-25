from main import *

rows = (
    supabase.table("video")
    .select("*")
    .order("published", desc=True)
    .execute()
    .dict()["data"]
)

# print(rows)


for row in rows:
    is_manim = is_manim_video(row["json"])
    supabase.table("video").update({"is_manim_video": is_manim}).eq("id", row["id"]).execute()

    print(row["summary"])
    print("###")
    print(is_manim)
    print("============\n\n")
    # import ipdb; ipdb.set_trace()
