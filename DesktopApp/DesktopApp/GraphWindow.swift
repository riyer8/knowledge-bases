import SwiftUI

struct GraphWindowView: View {
    let entries: [ManualInputEntry]
    @State private var selectedGraphEntryID: UUID?

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Files")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundColor(Color(hex: "#3d2b1f"))
                    Spacer()
                    Text("\(entries.count)")
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 10)
                .padding(.top, 10)

                List(entries) { entry in
                    Button {
                        selectedGraphEntryID = entry.id
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(entry.value)
                                .font(.system(size: 11, weight: .medium, design: .rounded))
                                .lineLimit(1)
                            Text(entry.kind.rawValue.uppercased())
                                .font(.system(size: 9, design: .rounded))
                                .foregroundColor(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 3)
                    }
                    .buttonStyle(.plain)
                    .listRowBackground(selectedGraphEntryID == entry.id ? Color(hex: "#fce7f3") : Color.clear)
                }
                .listStyle(.plain)
            }
            .frame(width: 128)
            .background(Color(hex: "#fff1f8"))

            Divider()

            GraphCanvasView(entries: entries, highlightedID: selectedGraphEntryID)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(hex: "#fff7fb"))
        }
    }
}

private struct GraphCanvasView: View {
    let entries: [ManualInputEntry]
    let highlightedID: UUID?

    var body: some View {
        GeometryReader { geo in
            let nodes = makeNodes(in: geo.size)
            ZStack {
                ForEach(Array(nodes.enumerated()), id: \.element.id) { index, node in
                    if index > 0 {
                        let previous = nodes[index - 1]
                        Path { p in
                            p.move(to: previous.point)
                            p.addLine(to: node.point)
                        }
                        .stroke(Color(hex: "#f9a8d4").opacity(0.55), lineWidth: 1.2)
                    }
                }

                ForEach(nodes, id: \.id) { node in
                    VStack(spacing: 3) {
                        Circle()
                            .fill(node.id == highlightedID ? Color(hex: "#ec4899") : Color(hex: "#f472b6"))
                            .frame(width: node.id == highlightedID ? 14 : 10, height: node.id == highlightedID ? 14 : 10)
                        Text(node.label)
                            .font(.system(size: 9, weight: .medium, design: .rounded))
                            .foregroundColor(Color(hex: "#3d2b1f"))
                            .lineLimit(1)
                            .frame(width: 90)
                    }
                    .position(node.point)
                }

                if nodes.isEmpty {
                    Text("No manual inputs yet.\nAdd files, URLs, or text to build your graph.")
                        .multilineTextAlignment(.center)
                        .font(.system(size: 12, design: .rounded))
                        .foregroundColor(.secondary)
                }
            }
            .padding(10)
        }
    }

    private func makeNodes(in size: CGSize) -> [GraphNode] {
        guard !entries.isEmpty else { return [] }
        let count = max(1, entries.count)
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let radius = max(46, min(size.width, size.height) / 2.6)

        return entries.enumerated().map { index, entry in
            let angle = (Double(index) / Double(count)) * (Double.pi * 2.0)
            let point = CGPoint(
                x: center.x + CGFloat(cos(angle)) * radius,
                y: center.y + CGFloat(sin(angle)) * radius
            )
            let label = String(entry.value.prefix(16))
            return GraphNode(id: entry.id, point: point, label: label)
        }
    }
}

private struct GraphNode {
    let id: UUID
    let point: CGPoint
    let label: String
}
