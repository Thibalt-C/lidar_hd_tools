from typing import List, Optional

def split_bbox(
        xmin : float,
        ymin : float,
        xmax : float,
        ymax : float,
        width : int,
        height : int,
        max_width : Optional[int] = 5000,
        max_height : Optional[int] = 5000
) -> List[dict] :

    tiles = []

    for row0 in range(0, height, max_height):

        row1 = min(row0 + max_height, height)

        y0 = ymax - (row0 / height) * (ymax - ymin)
        y1 = ymax - (row1 / height) * (ymax - ymin)

        for col0 in range(0, width, max_width):

            col1 = min(col0 + max_width, width)

            x0 = xmin + (col0 / width) * (xmax - xmin)
            x1 = xmin + (col1 / width) * (xmax - xmin)

            tiles.append(
                {
                    "bbox": (x0, y1, x1, y0),
                    "size": (col1 - col0, row1 - row0),
                    "row_slice": slice(row0, row1),
                    "col_slice": slice(col0, col1),
                }
            )

    return tiles