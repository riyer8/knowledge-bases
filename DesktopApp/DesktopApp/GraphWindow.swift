import SwiftUI
import Foundation
import Combine

struct GraphWindowView: View {
    @StateObject private var graphStore = MarkdownGraphStore()
    @Environment(\.colorScheme) private var colorScheme
    @State private var selectedNodeID: String?
    @State private var showOnlyOrphans = false
    @State private var showOnlyUnlinked = false
    @State private var selectedFolder = "All"
    private var isDarkMode: Bool { colorScheme == .dark }
    private var sidebarBackground: Color { isDarkMode ? Color(nsColor: .controlBackgroundColor) : Color(hex: "#fff1f8") }
    private var canvasBackground: Color { isDarkMode ? Color(nsColor: .underPageBackgroundColor) : Color(hex: "#fff7fb") }
    private var titleColor: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }
    private var selectedRowBackground: Color { isDarkMode ? Color.accentColor.opacity(0.25) : Color(hex: "#fce7f3") }

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Knowledge Graph")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundColor(titleColor)
                    Text("Browse markdown connections and filter by folder.")
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 10)
                .padding(.top, 8)

                HStack {
                    Text("Files")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundColor(titleColor)
                    Spacer()
                    Text("\(graphStore.graph.nodes.count)")
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 10)
                .padding(.top, 10)

                HStack(spacing: 6) {
                    Button {
                        Task { await refreshGraph() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                            .font(.system(size: 10, design: .rounded))
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)

                    if graphStore.isLoading {
                        ProgressView().scaleEffect(0.6)
                    }
                }
                .padding(.horizontal, 10)

                Toggle("Orphans only", isOn: $showOnlyOrphans)
                    .font(.system(size: 10, design: .rounded))
                    .padding(.horizontal, 10)
                    .onChange(of: showOnlyOrphans) {
                        Task { await refreshGraph() }
                    }

                Toggle("No outgoing links", isOn: $showOnlyUnlinked)
                    .font(.system(size: 10, design: .rounded))
                    .padding(.horizontal, 10)
                    .onChange(of: showOnlyUnlinked) {
                        Task { await refreshGraph() }
                    }

                Picker("Folder", selection: $selectedFolder) {
                    Text("All").tag("All")
                    ForEach(graphStore.graph.folders, id: \.self) { folder in
                        Text(folder).tag(folder)
                    }
                }
                .font(.system(size: 10, design: .rounded))
                .padding(.horizontal, 10)
                .onChange(of: selectedFolder) {
                    Task { await refreshGraph() }
                }

                if let error = graphStore.errorMessage {
                    Text(error)
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.red.opacity(0.85))
                        .padding(.horizontal, 10)
                }

                List(graphStore.graph.nodes) { node in
                    Button {
                        selectedNodeID = node.id
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(node.label)
                                .font(.system(size: 11, weight: .medium, design: .rounded))
                                .lineLimit(1)
                            Text("in:\(node.incoming) out:\(node.outgoing)")
                                .font(.system(size: 9, design: .rounded))
                                .foregroundColor(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 3)
                    }
                    .buttonStyle(.plain)
                    .listRowBackground(selectedNodeID == node.id ? selectedRowBackground : Color.clear)
                }
                .listStyle(.plain)
            }
            .frame(width: 220)
            .background(sidebarBackground)

            Divider()

            GraphCanvasView(graph: graphStore.graph, highlightedID: selectedNodeID)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(canvasBackground)
        }
        .task { await refreshGraph() }
    }

    private func refreshGraph() async {
        await graphStore.refresh(
            onlyOrphans: showOnlyOrphans,
            onlyUnlinked: showOnlyUnlinked,
            folder: selectedFolder == "All" ? nil : selectedFolder
        )
    }
}

private struct GraphCanvasView: View {
    let graph: MarkdownGraph
    let highlightedID: String?
    @Environment(\.colorScheme) private var colorScheme
    @State private var zoom: CGFloat = 1.0
    @State private var baseZoom: CGFloat = 1.0
    @State private var pan: CGSize = .zero
    @State private var basePan: CGSize = .zero
    private var isDarkMode: Bool { colorScheme == .dark }
    private var edgeColor: Color { isDarkMode ? Color.pink.opacity(0.45) : Color(hex: "#f9a8d4").opacity(0.45) }
    private var arrowColor: Color { isDarkMode ? Color.pink.opacity(0.85) : Color(hex: "#f472b6") }
    private var nodeTextColor: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }
    private var normalNodeColor: Color { isDarkMode ? Color.pink.opacity(0.8) : Color(hex: "#f472b6") }

    var body: some View {
        GeometryReader { geo in
            let nodes = makeNodes(in: geo.size)
            ZStack(alignment: .topTrailing) {
                ZStack {
                    ForEach(graph.edges) { edge in
                        if let source = nodes.first(where: { $0.id == edge.source }),
                           let target = nodes.first(where: { $0.id == edge.target }) {
                            Path { p in
                                p.move(to: source.point)
                                p.addLine(to: target.point)
                            }
                            .stroke(edgeColor, lineWidth: 1.0)
                            drawArrowHead(from: source.point, to: target.point)
                                .fill(arrowColor)
                        }
                    }

                    ForEach(nodes, id: \.id) { node in
                        VStack(spacing: 3) {
                            Circle()
                                .fill(node.id == highlightedID ? Color(hex: "#ec4899") : normalNodeColor)
                                .frame(width: node.id == highlightedID ? 16 : 11, height: node.id == highlightedID ? 16 : 11)
                            Text(node.label)
                                .font(.system(size: 9, weight: .medium, design: .rounded))
                                .foregroundColor(nodeTextColor)
                                .lineLimit(1)
                                .frame(width: 130)
                        }
                        .position(node.point)
                    }

                    if nodes.isEmpty {
                        Text("No markdown files found.\nAdd .md files to build your graph.")
                            .multilineTextAlignment(.center)
                            .font(.system(size: 12, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                }
                .scaleEffect(zoom)
                .offset(pan)
                .animation(.interactiveSpring(response: 0.22, dampingFraction: 0.9), value: pan)
                .animation(.interactiveSpring(response: 0.22, dampingFraction: 0.9), value: zoom)
                .simultaneousGesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { value in
                            pan = CGSize(
                                width: basePan.width + value.translation.width,
                                height: basePan.height + value.translation.height
                            )
                        }
                        .onEnded { value in
                            basePan = CGSize(
                                width: basePan.width + value.translation.width,
                                height: basePan.height + value.translation.height
                            )
                            pan = basePan
                        }
                )
                .simultaneousGesture(
                    MagnificationGesture()
                        .onChanged { value in
                            zoom = max(0.45, min(3.0, baseZoom * value))
                        }
                        .onEnded { value in
                            baseZoom = max(0.45, min(3.0, baseZoom * value))
                            zoom = baseZoom
                        }
                )

                Button("Reset View") {
                    baseZoom = 1.0
                    zoom = 1.0
                    basePan = .zero
                    pan = .zero
                }
                .font(.system(size: 10, design: .rounded))
                .padding(8)
            }
            .padding(10)
        }
    }

    private func makeNodes(in size: CGSize) -> [GraphNode] {
        guard !graph.nodes.isEmpty else { return [] }
        let count = max(1, graph.nodes.count)
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let radius = max(46, min(size.width, size.height) / 2.6)

        return graph.nodes.enumerated().map { index, node in
            let angle = (Double(index) / Double(count)) * (Double.pi * 2.0)
            let point = CGPoint(
                x: center.x + CGFloat(cos(angle)) * radius,
                y: center.y + CGFloat(sin(angle)) * radius
            )
            let label = String(node.label.prefix(16))
            return GraphNode(id: node.id, point: point, label: label)
        }
    }

    private func drawArrowHead(from: CGPoint, to: CGPoint) -> Path {
        let dx = to.x - from.x
        let dy = to.y - from.y
        let angle = atan2(dy, dx)
        let headLength: CGFloat = 8
        let headAngle: CGFloat = .pi / 7

        let p1 = CGPoint(
            x: to.x - headLength * cos(angle - headAngle),
            y: to.y - headLength * sin(angle - headAngle)
        )
        let p2 = CGPoint(
            x: to.x - headLength * cos(angle + headAngle),
            y: to.y - headLength * sin(angle + headAngle)
        )
        var path = Path()
        path.move(to: to)
        path.addLine(to: p1)
        path.addLine(to: p2)
        path.closeSubpath()
        return path
    }
}

private struct MarkdownGraph: Codable {
    var nodes: [GraphNodeDTO] = []
    var edges: [GraphEdgeDTO] = []
    var folders: [String] = []
}

private struct GraphNodeDTO: Codable, Identifiable {
    let id: String
    let label: String
    let path: String
    let folder: String
    let incoming: Int
    let outgoing: Int
    let degree: Int
    let isOrphan: Bool
    let isUnlinked: Bool
}

private struct GraphEdgeDTO: Codable, Identifiable {
    var id: String { "\(source)->\(target)" }
    let source: String
    let target: String
}

@MainActor
private final class MarkdownGraphStore: ObservableObject {
    @Published var graph = MarkdownGraph()
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let baseURL = URL(string: "http://127.0.0.1:8765")!

    func refresh(onlyOrphans: Bool = false, onlyUnlinked: Bool = false, folder: String? = nil) async {
        isLoading = true
        defer { isLoading = false }
        do {
            var components = URLComponents(url: baseURL.appendingPathComponent("graph"), resolvingAgainstBaseURL: false)
            var items: [URLQueryItem] = [
                URLQueryItem(name: "orphans", value: onlyOrphans ? "1" : "0"),
                URLQueryItem(name: "unlinked", value: onlyUnlinked ? "1" : "0"),
            ]
            if let folder, !folder.isEmpty {
                items.append(URLQueryItem(name: "folder", value: folder))
            }
            components?.queryItems = items
            let requestURL = components?.url ?? baseURL.appendingPathComponent("graph")

            let (data, response) = try await URLSession.shared.data(from: requestURL)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            graph = try JSONDecoder().decode(MarkdownGraph.self, from: data)
            errorMessage = nil
        } catch {
            errorMessage = "Graph backend unavailable."
        }
    }
}

private struct GraphNode {
    let id: String
    let point: CGPoint
    let label: String
}
