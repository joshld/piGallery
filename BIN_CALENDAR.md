# Brisbane bin collection

Bin icons sit on top of the photos. They use the existing `piGallery.service` and the web controls at `http://cheesecake.local:5000/`. There is no extra service.

## What you can set

On the status page, open **Bin collection**:

- The street address used for the council lookup. Pick the matching property, then save.
- Which bins to show: general waste (red), recycling (yellow), and garden waste (green). Green is off until you turn it on.
- Where each icon sits on the frame. Icons that share a spot are drawn together.
- Icon size, from half to double the normal size.
- How many days before collection the icons stay on the photos. The default is 2, so a Friday collection is on screen all of Wednesday, Thursday and Friday. Outside that window the photos are left clear.

Bin choices are saved with the same **Save Settings** button as the rest of the page. The frame redraws the current photo straight away.
- How often to ask the council for new dates. `1` day means daily, at the Brisbane time you choose.

Dates are the next published collection for each bin. The frame keeps the last successful dates if the network is down. A manual refresh is available from the same panel.

Top left is where the clock sits, top right is the weather, and the bottom can cover a caption. The default place is top centre so the icons start in the open gap.

## Data

Source: [Brisbane City Council bin collection calendar](https://data.brisbane.qld.gov.au/explore/dataset/bin-collection-calendar/api/).

`https://data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/bin-collection-calendar/records`

The cache is `.cache/bin-calendar.json`. `config.ini` and `.cache/` are not committed. Do not put a real address in the repository.

```sh
sudo systemctl restart piGallery.service
curl -X POST http://127.0.0.1:5000/api/bin-calendar/refresh
```
