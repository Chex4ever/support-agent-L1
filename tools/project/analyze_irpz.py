# Analyze an iRidi Studio project (.irpz) — list pages, popups, items, tokens, scripts, devices
# Usage: python tools/project/analyze_irpz.py path/to/project.irpz
# Example: python tools/project/analyze_irpz.py tickets/422-279121/files/list\ problem.irpz

import zipfile, re, sys, os

def analyze(path):
    with zipfile.ZipFile(path, "r") as z:
        # Parse Project.irp for high-level structure
        proj = z.read("Project.irp").decode("utf-8", errors="replace")

        print(f"=== Project: {os.path.basename(path)} ===\n")

        # Project info
        panel_match = re.search(r'<Panel[^>]*>', proj)
        if panel_match:
            w = re.search(r'Width="(\d+)"', panel_match.group())
            h = re.search(r'Height="(\d+)"', panel_match.group())
            t = re.search(r'ProjectType="(\d+)"', panel_match.group())
            ptype = "Panel" if t and t.group(1) == "1" else "Server" if t and t.group(1) == "2" else f"Type {t.group(1) if t else '?'}"
            print(f"Type: {ptype}, Size: {w.group(1) if w else '?'}x{h.group(1) if h else '?'}")
        print()

        # Devices
        devices = re.findall(r'<Device[^>]*Name="([^"]+)"', proj)
        print(f"Devices ({len(devices)}): {', '.join(devices) if devices else '(none)'}")

        # Scripts
        scripts = re.findall(r'<Script Name="([^"]+)" File="([^"]+)"', proj)
        print(f"\nScripts ({len(scripts)}):")
        for name, file in scripts:
            print(f"  {name} -> {file}")
            # Show first line of script content
            try:
                content = z.read(f"scripts/{file}").decode("utf-8", errors="replace")
                first_line = content.split("\n")[0].strip()
                print(f"    ({first_line})")
            except KeyError:
                pass

        # Project Tokens (VirtualTags)
        tokens = re.findall(r'<VirtualTag Name="([^"]+)"', proj)
        print(f"\nProject Tokens ({len(tokens)}): {', '.join(tokens) if tokens else '(none)'}")

        # RelationTags (bindings)
        rels = re.findall(r'<RelationTags LHS="([^"]+)" RHS="([^"]+)"', proj)
        if rels:
            print(f"\nBindings (RelationTags):")
            for lhs, rhs in rels:
                print(f"  {lhs} <-> {rhs}")

        # Pages
        pages = re.findall(r'<Page Name="([^"]+)"[^>]*>', proj)
        print(f"\nPages ({len(pages)}):")
        for page_name in pages:
            page_section = re.search(rf'<Page Name="{re.escape(page_name)}">(.*?)</Page>', proj, re.DOTALL)
            if page_section:
                items = re.findall(r'<Item Name="([^"]+)" Type="(\d+)"[^>]*>', page_section.group(1))
                print(f"  {page_name}:")
                for item_name, item_type in items:
                    sit_match = re.search(rf'<Item Name="{re.escape(item_name)}" [^>]*SIT="(\d+)"', page_section.group(1))
                    sit = sit_match.group(1) if sit_match else "?"
                    # Get text if label
                    text_match = re.search(rf'<Item Name="{re.escape(item_name)}".*?<Text[^>]*Text="([^"]*)"', page_section.group(1), re.DOTALL)
                    label_text = text_match.group(1) if text_match else ""
                    display_text = f' = "{label_text}"' if label_text and item_type == "0" else ""
                    print(f"    [{item_type}] {item_name}{display_text}")

        # Popups
        popups = re.findall(r'<Popup Name="([^"]+)"[^>]*>', proj)
        print(f"\nPopups ({len(popups)}):")
        for popup_name in popups:
            popup_section = re.search(rf'<Popup Name="{re.escape(popup_name)}">(.*?)</Popup>', proj, re.DOTALL)
            if popup_section:
                items = re.findall(r'<Item Name="([^"]+)" Type="(\d+)"[^>]*>', popup_section.group(1))
                print(f"  {popup_name}:")
                for item_name, item_type in items:
                    # Get text if label
                    text_match = re.search(rf'<Item Name="{re.escape(item_name)}".*?<Text[^>]*Text="([^"]*)"', popup_section.group(1), re.DOTALL)
                    label_text = text_match.group(1) if text_match else ""
                    display_text = f' = "{label_text}"' if label_text and item_type == "0" else ""
                    print(f"    [{item_type}] {item_name}{display_text}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/project/analyze_irpz.py <path_to.irpz>")
        sys.exit(1)
    analyze(sys.argv[1])
