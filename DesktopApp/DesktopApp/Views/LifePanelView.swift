import SwiftUI

struct LifePanelView: View {
    @ObservedObject var lifeStore: LifeStore
    let panelTitleColor: Color
    let sectionBackground: Color
    @State private var showPeople = false

    var body: some View {
        HSplitView {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Label(showPeople ? "People" : "Time", systemImage: showPeople ? "person.2" : "chart.pie")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundColor(panelTitleColor)
                    Spacer()
                    Button {
                        Task { await lifeStore.refreshAll() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .buttonStyle(.borderless)
                }
                .padding(.horizontal, 12)
                .padding(.top, 10)

                Picker("View", selection: $showPeople) {
                    Text("Time").tag(false)
                    Text("People").tag(true)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal, 12)

                if lifeStore.isLoading {
                    ProgressView("Loading…")
                        .font(.system(size: 11, design: .rounded))
                        .padding()
                }

                if showPeople {
                    List(lifeStore.profiles) { profile in
                        Button {
                            lifeStore.selectedProfile = profile
                            lifeStore.editNotes = profile.notes
                        } label: {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(profile.displayName)
                                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                                    .foregroundColor(panelTitleColor)
                                Text("\(profile.eventCount) interactions")
                                    .font(.system(size: 10, design: .rounded))
                                    .foregroundColor(.secondary)
                            }
                        }
                        .buttonStyle(.plain)
                    }
                    .listStyle(.plain)
                } else {
                    List(lifeStore.summary?.breakdown ?? []) { item in
                        HStack {
                            Text(item.bucket)
                                .font(.system(size: 12, design: .rounded))
                                .foregroundColor(panelTitleColor)
                            Spacer()
                            Text("\(item.count) · \(item.percent, specifier: "%.0f")%")
                                .font(.system(size: 10, design: .rounded))
                                .foregroundColor(.secondary)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .frame(minWidth: 180, idealWidth: 220, maxWidth: 280)

            VStack(alignment: .leading, spacing: 10) {
                if showPeople {
                    if let profile = lifeStore.selectedProfile {
                        Text(profile.displayName)
                            .font(.system(size: 15, weight: .semibold, design: .rounded))
                            .foregroundColor(panelTitleColor)
                        Text("\(profile.eventCount) captured interactions")
                            .font(.system(size: 11, design: .rounded))
                            .foregroundColor(.secondary)
                        Text("Notes")
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                        TextEditor(text: $lifeStore.editNotes)
                            .font(.system(size: 12, design: .rounded))
                            .frame(minHeight: 120)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.secondary.opacity(0.2))
                            )
                        Button("Save notes") {
                            Task { await lifeStore.saveNotes(for: profile) }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(Color(hex: "#ec4899"))
                    } else {
                        Text("Select a person to view or edit their profile.")
                            .font(.system(size: 12, design: .rounded))
                            .foregroundColor(.secondary)
                            .padding()
                    }
                } else if let summary = lifeStore.summary {
                    Text("How you spend your time")
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundColor(panelTitleColor)
                    Text("Last \(summary.days) days · \(summary.eventCount) classified events")
                        .font(.system(size: 11, design: .rounded))
                        .foregroundColor(.secondary)

                    ForEach(summary.byTopLevel) { category in
                        HStack {
                            Text(category.category)
                                .font(.system(size: 12, weight: .medium, design: .rounded))
                            Spacer()
                            Text("\(category.percent, specifier: "%.0f")%")
                                .font(.system(size: 12, design: .rounded))
                                .foregroundColor(Color(hex: "#ec4899"))
                        }
                        GeometryReader { geo in
                            RoundedRectangle(cornerRadius: 4)
                                .fill(Color(hex: "#ec4899").opacity(0.2))
                                .frame(width: geo.size.width * CGFloat(category.percent / 100.0))
                        }
                        .frame(height: 8)
                    }
                } else {
                    Text("No bucket data yet. Capture screen activity or add manual inputs.")
                        .font(.system(size: 12, design: .rounded))
                        .foregroundColor(.secondary)
                        .padding()
                }
                Spacer()
            }
            .padding(12)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(sectionBackground)
        }
        .task { await lifeStore.refreshAll() }
    }
}
