動画のアノテーションを行うためのツール

初めに:init.bat
実行時:start.bat

画像の出力
mode:
    folder(default):フォルダーで危険かそうでないかを分類
    name:名前で危険かそうでないかを分類/連続している領域は同じフォルダーに入る
一回だけ:.\venv\Scripts\activate
その後:python ImageExtractor.py <VideoPath> <OutputFolder> <fps> [mode|name,folder]