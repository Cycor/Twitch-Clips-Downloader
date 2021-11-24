import requests, os, argparse
import os.path
from slugify import slugify
from time import sleep
from pprint import pprint


def MarkDone(artist, folder, slug):
    filename = u"{}/{}_done.txt".format(folder, artist)
    with open(filename, "a+") as myfile:
        myfile.write("{}\n".format(slug))

def AlreadyDownloaded(artist, folder, slug):
    filename = u"{}/{}_done.txt".format(folder, artist)
    if os.path.isfile(filename):
        with open(filename) as myfile:
           if slug in myfile.read():
               return True
    return False

def ExportJson(folder, filename, clip):
    filename = u"{}/{}.json".format(folder, filename)
    with open(filename, "a+") as myfile:
        pprint.pprint(clip, myfile)
        myfile.write(",\n")

def ExportList(folder, filename, clip):
    filename = u"{}/{}.txt".format(folder, filename)

    slug = clip['node']['slug']
    created_at = clip['node']['createdAt'].split('T')[0]
    title = clip['node']['title'].strip()
    if clip['node']['game'] != None:
        game = "[{}]".format(clip['node']['game']['name'].strip())
    else:
        game = ""

    line =  u"{} {} - {} {}[{}]".format(created_at, Twitch_Username, title, game, slug)

    with open(filename, "a+") as myfile:
        myfile.write("{}\n".format(line))

def GetClipUrl(slug):
    data = [{"operationName":"VideoAccessToken_Clip","variables":{"slug":slug},"extensions":{"persistedQuery":{"version":1,"sha256Hash":"9bfcc0177bffc730bd5a5a89005869d2773480cf1738c592143b5173634b7d15"}}}]
    r = requests.post("https://gql.twitch.tv/gql", headers={"Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko"}, json=data)
    try:
        url = r.json()[0]['data']['clip']['videoQualities'][0]['sourceURL']
        return url.replace("https://production.assets.clips.twitchcdn.net/", "https://clips-media-assets2.twitch.tv/")
    except:
        print("[ERROR] Could not fetch clip URL")
        return None

def DownloadClip(folder, clip):

    slug = clip['node']['slug']
    artist = clip['node']['broadcaster']['login']

    if not AlreadyDownloaded(artist, folder, slug):

        created_at = clip['node']['createdAt'].split('T')[0]
        title = clip['node']['title'].strip()
        if clip['node']['game'] != None:
           game = '[{}]'.format(clip['node']['game']['name'].strip())
        else:
           game = ''

        filename = u"{} {} - {} {}[{}].mp4".format(created_at, Twitch_Username, title, game, slug)
        filename = "".join([c for c in filename if c.isalnum() or c in '.,_- []()!\'+"']).rstrip()
        filepath = u"{}/{}/{}".format(folder, artist, filename)

        if not os.path.isfile(filepath):
            clip_url = GetClipUrl(slug)
            if clip_url != None:
                r = requests.get(clip_url)
                with open(filepath, 'xb') as f:
                    f.write(r.content)
                b = os.path.getsize(filepath)
                if b > 0:
                    print(u"[SUCCESS] Saved as {}".format(filename))
                    MarkDone(artist, folder, slug)
                else:
                    print(u"[ERROR] Filesize is 0 {}".format(filename))
                    os.remove(filepath)
        else:
            print("[SKIPPED] File already exists {}".format(filename))
            MarkDone(artist, folder, slug)
    else:
        MarkDone(artist, folder, slug)
#        print("[SKIPPED] Already downloaded this file {}".format(filename))


# Create the parser
my_parser = argparse.ArgumentParser(description='Downloads your Twitch clips')

# Add the arguments
my_parser.add_argument('Username', metavar='username', type=str, help='Twitch channel you want to download clips from')
my_parser.add_argument('--folder', required=False)
my_parser.add_argument('--limit', required=False)
my_parser.add_argument('--range', type=str, help='Range: LAST_DAY, LAST_WEEK, LAST_MONTH, ALL_TIME', required=False)
my_parser.add_argument('--export', type=str, help='Export list of clips without downloading')

# Execute the parse_args() method
args = my_parser.parse_args()

Twitch_Username = args.Username
if args.limit != None:
    Clips_Limit = int(args.limit)
else:
    Clips_Limit = None

if args.range != None:
    Range_List = [args.range]
else:
    Range_List = None

if args.export != None:
    Export = args.export
else:
    Export = None

if args.folder != None:
    Folder = args.folder
else:
    Folder = "./top-clips"

try:
    os.mkdir(Folder)
    print("[SUCCESS] Directory {} Created".format(Folder))
except FileExistsError:
    print("[INFO] Directory {} already exists".format(Folder))
try:
    os.mkdir("{}/{}".format(Folder, Twitch_Username))
    print("[SUCCESS] Directory {}/{} Created ".format(Folder, Twitch_Username))
except FileExistsError:
    print("[INFO] Directory {}/{} already exists".format(Folder, Twitch_Username))

nextPage = True

if Range_List == None:
    Range_List = ["ALL_TIME"]

    if Clips_Limit == None:
        Range_List = ["LAST_DAY", "LAST_WEEK", "LAST_MONTH", "ALL_TIME"]

for Range in Range_List:
    doneParsing = False
    cursor = None
    i = 1

    print("Range {}".format(Range))
    while not doneParsing:
        data = [{"operationName":"ClipsCards__User","variables":{"login":Twitch_Username,"limit":20, "cursor": cursor, "criteria":{"filter":Range}},"extensions":{"persistedQuery":{"version":1,"sha256Hash":"b73ad2bfaecfd30a9e6c28fada15bd97032c83ec77a0440766a56fe0bd632777"}}}]
        r = requests.post("https://gql.twitch.tv/gql", headers={"Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko"}, json=data)
        if "errors" not in r.json()[0]:
#            pprint(r.json()[0])

            nextPage = r.json()[0]['data']['user']['clips']['pageInfo']['hasNextPage']
            clips = r.json()[0]['data']['user']['clips']['edges']
            for clip in clips:
                if Export != None:
                    ExportList(Folder, Export, clip)
                else:
                    if Clips_Limit != None:
                        if i <= Clips_Limit:
                            DownloadClip(Folder, clip)
                        else:
                            doneParsing = True
                    else:
                        DownloadClip(Folder, clip)
                i = i + 1
            if not r.json()[0]['data']['user']['clips']['pageInfo']['hasNextPage']:
                doneParsing = True
            cursor = clips[len(clips) - 1]['cursor']
            if doneParsing:
                print("[SUCCESS] Fetched {} clips from {}".format(int(i - 1), Range))
        else:
            if r.json()[0]['errors'][0]['message'] == "service timeout":
                print("[TIMEOUT] Received rate-limit, waiting 5 seconds...")
                sleep(5)

if len(Range_List) > 1:
    print("[SUCCESS] Reached clips limit, maximum amount of clips retrieved")
else:
    print("[SUCCESS] Finished fetching clips")
